from typing import Dict, List, Set, Tuple, Callable, Optional, Any
from langchain_neo4j import Neo4jGraph
import re

class CustomNeo4jGraph(Neo4jGraph):
    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        timeout: Optional[float] = None,
        sanitize: bool = False,
        refresh_schema: bool = True,
        *,
        driver_config: Optional[Dict] = None,
        enhanced_schema: bool = False,
    ):
        super().__init__(
            url=url,
            username=username,
            password=password,
            database=database,
            timeout=timeout,
            sanitize=sanitize,
            refresh_schema=refresh_schema,
            driver_config=driver_config,
            enhanced_schema=enhanced_schema
        )
        self.custom_structured_schema = self._gen_custom_structured_schema()
    
    def _gen_custom_structured_schema(self):
        """
        get_structured_schema로 얻을 수 있는 스미카와 동일한 구조이나 속성명이 키인 딕셔너리 형태의 구조화된 스키마 생성
        """
        original_structured_schema = self.get_structured_schema
        custom_schema = {
            "node_props": {},
            "rel_props": {},
            "relationships": [],
            "metadata": {}
        }
        
        # 노드 속성
        for node_label, props in original_structured_schema.get("node_props", {}).items():
            custom_schema["node_props"][node_label] = {prop["property"]: prop for prop in props}
        
        # 관계 속성
        for rel_type, props in original_structured_schema.get("rel_props", {}).items():
            custom_schema["rel_props"][rel_type] = {prop["property"]: prop for prop in props}
            
        # 관계
        for rel in original_structured_schema.get("relationships", []):
            if rel["type"] not in custom_schema["rel_props"]:
                custom_schema["rel_props"][rel["type"]] = {}
        
        custom_schema["relationships"] = original_structured_schema.get("relationships", [])
        custom_schema["metadata"] = original_structured_schema.get("metadata", {})
        
        return custom_schema
        
    @property
    def get_custom_structured_schema(self) -> Dict[str, Any]:
        return self.custom_structured_schema
    
    
class ChainedCorrector:
    def __init__(self,
                first: Callable[[str], str],
                second: Callable[[str], str]):
        self.first  = first
        self.second = second

    def __call__(self, query: str) -> str:
        return self.second(self.first(query))
    

class CypherValidator:
    def __init__(self, graph):
        self.graph = graph
        self.schema = graph.get_custom_structured_schema
    
    def _parse_properties_string(self, props_str: str):
        """Cypher에서 중괄호 안의 속성 문자열을 파싱하여 속성 이름들 추출"""
        properties = set()
        
        # 속성명만 추출 (콜론 앞의 부분)
        prop_matches = re.findall(r'\`?([a-zA-Z0-9가-힣]+)\`?\s*:', props_str)
        properties.update(prop_matches)
        
        return properties
        
    def _extract_cypher_elements(self, cypher_query: str):
        """Cypher에서 엘리먼트들 추출"""
        elements = {
            'node_labels': set(),
            'relationship_types': set(),
            'node_properties': {},  
            'relationship_properties': {}
        }
        
        # 1. 노드 패턴 추출 (중괄호 내의 속성 포함)
        # 패턴: (변수:레이블 {속성들}) 또는 (:레이블 {속성들})
        node_pattern = r'\((?:(\w):)?\`?([a-zA-Z0-9가-힣]+)\`?(?:\s*\{([^}]*)\})?\)'
        node_matches = re.findall(node_pattern, cypher_query, re.IGNORECASE)

        var_to_label = {}
        for var, label, props_str in node_matches:
            elements['node_labels'].add(label)
            if var:  # 변수가 있는 경우
                var_to_label[var] = label
            
            # 중괄호 안의 속성들 파싱
            if props_str:
                props = self._parse_properties_string(props_str)
                if label not in elements['node_properties']:
                    elements['node_properties'][label] = set()
                elements['node_properties'][label].update(props)
        
        # 2. 관계 패턴 추출 (중괄호 속성 포함)
        # 패턴: -[변수:관계타입 {속성들}]- 또는 -[:관계타입 {속성들}]-
        rel_pattern = r'-\[(?:(\w+):)?\`?([a-zA-Z0-9가-힣]+)\`?(?:\s*\{([^}]*)\})?\]-'
        rel_matches = re.findall(rel_pattern, cypher_query, re.IGNORECASE)
        
        var_to_rel_type = {}
        for var, rel_type, props_str in rel_matches:
            elements['relationship_types'].add(rel_type)
            if var:  # 변수가 있는 경우
                var_to_rel_type[var] = rel_type
            
            # 중괄호 안의 속성들 파싱
            if props_str:
                props = self._parse_properties_string(props_str)
                if rel_type not in elements['relationship_properties']:
                    elements['relationship_properties'][rel_type] = set()
                elements['relationship_properties'][rel_type].update(props)
        
        # 3. 일반 속성 참조 추출 (변수.속성 형태)
        prop_pattern = r'(\w+)\.\`?([a-zA-Z0-9가-힣]+)\`?'
        prop_matches = re.findall(prop_pattern, cypher_query)
        
        for var, prop in prop_matches:
            # 노드 속성인지 확인
            if var in var_to_label:
                label = var_to_label[var]
                if label not in elements['node_properties']:
                    elements['node_properties'][label] = set()
                elements['node_properties'][label].add(prop)
            
            # 관계 속성인지 확인
            elif var in var_to_rel_type:
                rel_type = var_to_rel_type[var]
                if rel_type not in elements['relationship_properties']:
                    elements['relationship_properties'][rel_type] = set()
                elements['relationship_properties'][rel_type].add(prop)
        
        return elements  
                
    def validate_cypher(self, cypher_query: str):
        """생성된 Cypher 쿼리 검증"""
        errors = []
        elements = self._extract_cypher_elements(cypher_query)
        
        # 노드 레이블 검증
        available_node_labels = set(self.schema.get('node_props', {}).keys())
        invalid_labels = elements['node_labels'] - available_node_labels
        if invalid_labels:
            errors.append(f"존재하지 않는 노드 레이블: {list(invalid_labels)}")
        
        # 관계 타입 검증
        available_rel_types = set(self.schema.get('rel_props', {}).keys())
        invalid_rels = elements['relationship_types'] - available_rel_types
        if invalid_rels:
            errors.append(f"존재하지 않는 관계 타입: {list(invalid_rels)}")
        
        # 노드 속성 검증 (MATCH 절 중괄호 + 일반 속성 참조)
        for label, props in elements['node_properties'].items():
            print(label, props)
            if label in self.schema.get('node_props', {}):
                available_props = set(self.schema['node_props'][label].keys())
                invalid_props = props - available_props
                if invalid_props:
                    errors.append(f"노드 '{label}'에 존재하지 않는 속성: {list(invalid_props)}")
        
        # 관계 속성 검증 (MATCH 절 중괄호 + 일반 속성 참조)
        for rel_type, props in elements['relationship_properties'].items():
            if rel_type in self.schema.get('rel_props', {}):
                available_props = set(self.schema['rel_props'][rel_type].keys())
                invalid_props = props - available_props
                if invalid_props:
                    errors.append(f"관계 '{rel_type}'에 존재하지 않는 속성: {list(invalid_props)}")
        
        return len(errors) == 0, errors
    
    def __call__(self, query: str):
        print("####################################")
        print("Validate cypher")
        print(self.validate_cypher(query))
        print("####################################", flush=True)
        return query
