from typing import Dict, Any, List, Optional, Type
from langchain_core.tools import BaseTool, ArgsSchema
from pydantic import BaseModel, Field
from app.core.tools.map.base import BaseToolKit, SafeValidationTool
from app.models.graphmodel.graph import AsyncGraphCypherQAChain
from app.core.tools.neo4j.cypher_analyzer import CypherDecomposer
import asyncio
import time
import json


class Neo4jSearchInput(BaseModel):
    query: str = Field(description="검색할 사용자 쿼리")
    expand_search: bool = Field(description="case1(False): 정확매치, case2(True): 조건완화", default=True)


class Neo4jSearchOutput(BaseModel):
    search_strategy: str = Field(description="case_1 또는 case_2")
    total_queries: int = Field(description="실행된 쿼리 수")
    query_results: List[Dict[str, Any]] = Field(description="각 쿼리별 상세 결과")
    aggregated_products: List[Dict[str, Any]] = Field(description="통합된 상품 정보")
    total_products: int = Field(description="총 상품 수")


class Neo4jSearchTool(SafeValidationTool):
    name: str = "neo4j_product_search"
    description: str = "Neo4j 데이터베이스에서 상품 정보 검색 (case1: 정확매치, case2: 조건완화)"
    args_schema: ArgsSchema | None = Neo4jSearchInput
    response_model: Type[BaseModel] = Neo4jSearchOutput
    status: bool = True
    
    def __init__(self, cypher_qa_chain: AsyncGraphCypherQAChain, llm_model=None, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'cypher_qa_chain', cypher_qa_chain)
        object.__setattr__(self, 'llm_model', llm_model or cypher_qa_chain.llm)
    
    def _get_fewshot_from_state(self, execution_context) -> list:
        """실행 컨텍스트에서 few-shot 예제 가져오기"""
        # execute_node에서 state.fewshot_examples를 전달받아 사용
        return getattr(execution_context, 'fewshot_examples', [])
    
    def _run(self, query: str, expand_search: bool = True) -> str:
        """동기 실행 (추상 메서드 구현)"""
        import asyncio
        return asyncio.run(self._arun(query, expand_search))
    
    async def _arun(self, query: str, expand_search: bool = True, fewshot_examples: list = None) -> str:
        """툴 실행 메인 함수 - 원본 map-search-agent 로직"""
        start_time = time.time()
        
        try:
            # Neo4j 드라이버 연결 확인 및 초기화
            if not self.cypher_qa_chain.db._driver:
                await self.cypher_qa_chain.db.connect()
            
            # Few-shot 예제는 execute_node에서 전달받음
            fewshot_examples = fewshot_examples or []
            
            # 1. 기본 검색 실행 (case1 시도) - few-shot 예제 포함
            result = await self.cypher_qa_chain.ainvoke(
                prompt="사용자 질의에 맞는 상품 정보를 Neo4j에서 검색하세요.",
                question=query,
                fewshot_examples=fewshot_examples
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            raw_data = result.get("result", [])
            cypher_query = result.get("cypher", "")
            
            # Case 1: 기본 검색 성공
            if raw_data and result.get("result") != "I don't know the answer.":
                return json.dumps({
                    "case": "1",
                    "cypher": cypher_query,
                    "result": result.get("result", ""),
                    "raw_data": raw_data,
                    "execution_time_ms": execution_time,
                    "result_metadata": {
                        "validated": True,
                        "search_strategy": "exact_match"
                    }
                }, ensure_ascii=False)
            
            # Case 2: 검색 실패시 조건 완화 검색 적용 (expand_search=True인 경우만)
            if expand_search:
                # CypherDecomposer를 사용하여 조건 분해
                decomposer = CypherDecomposer(llm_model=self.llm_model)
                sub_queries = decomposer.decompose(
                    base_cypher=cypher_query,
                    original_question=query
                )
                
                # sub_queries에 있는 cypher들을 각각 실행해보고 결과 수집
                cypher_results = []
                for sub_cypher in sub_queries:
                    try:
                        # AsyncGraphCypherQAChain으로 각 서브쿼리 실행
                        sub_result = await self.cypher_qa_chain.ainvoke(
                            prompt="조건을 완화한 상품 검색을 수행하세요.",
                            question="", # 이미 cypher가 생성된 상태
                            return_cypher_only=False
                        )
                        sub_data = sub_result.get("records", [])
                        cypher_results.append(sub_data)
                    except Exception as e:
                        print(f"서브쿼리 실행 실패: {e}")
                        cypher_results.append([])
                
                total_execution_time = int((time.time() - start_time) * 1000)
                
                return json.dumps({
                    "case": "2",
                    "cypher": sub_queries,  # 리스트!
                    "result": "",
                    "raw_data": cypher_results,  # 리스트의 리스트!
                    "execution_time_ms": total_execution_time,
                    "result_metadata": {
                        "validated": True,
                        "search_strategy": "condition_relaxation",
                        "sub_queries_count": len(sub_queries)
                    }
                }, ensure_ascii=False)
            
            # expand_search=False인데 실패한 경우
            else:
                return json.dumps({
                    "case": "1",
                    "cypher": cypher_query,
                    "result": "검색 결과가 없습니다.",
                    "raw_data": [],
                    "execution_time_ms": execution_time,
                    "result_metadata": {
                        "validated": True,
                        "search_strategy": "exact_match_only",
                        "no_results": True
                    }
                }, ensure_ascii=False)
                
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return json.dumps({
                "case": "1",
                "cypher": "",
                "result": f"검색 실행 중 오류 발생: {str(e)}",
                "raw_data": [],
                "execution_time_ms": execution_time,
                "result_metadata": {
                    "validated": False,
                    "error": str(e)
                }
            }, ensure_ascii=False)


class Neo4jToolKit(BaseToolKit):
    """Neo4j 검색 툴킷"""
    
    def __init__(self, cypher_qa_chain: AsyncGraphCypherQAChain, llm_model=None, status: bool = True):
        self.cypher_qa_chain = cypher_qa_chain
        self.llm_model = llm_model
        self.status = status
    
    def get_tools(self) -> List[BaseTool]:
        """Neo4j 검색 툴 반환"""
        neo4j_tool = Neo4jSearchTool(self.cypher_qa_chain, self.llm_model)
        neo4j_tool.status = self.status
        return [neo4j_tool]