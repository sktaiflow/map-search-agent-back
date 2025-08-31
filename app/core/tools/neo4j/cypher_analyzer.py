import re
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


class CypherDecomposer:
    """Cypher 쿼리 분해 클래스 - case2용 조건 완화 검색"""
    
    def __init__(self, llm_model: ChatOpenAI):
        self.llm_model = llm_model
    
    def _match_to_where(self, cypher: str):
        """
        MATCH 절의 속성값 조건을 WHERE 절로 옮기기
        """
        conds = []
        # MATCH 절에서 alias와 속성 블록을 찾아 조건으로 변환
        for alias, props in re.findall(r"\((\w+)[^{}]*\{([^}]+)\}\)", cypher):
            for part in props.split(","):
                if ":" in part:
                    key, val = part.split(":", 1)
                    conds.append(f"{alias}.{key.strip()} = {val.strip()}")
        
        # MATCH 절 내의 {...} 부분 제거
        cypher = re.sub(r"\s*\{[^}]*\}", "", cypher)
        
        # WHERE 절 추가
        if conds:
            if re.search(r"(?i)\bWHERE\b", cypher):
                # 기존 WHERE 뒤에 추가
                cypher = re.sub(
                    r"(?i)(\bWHERE\b)",
                    lambda m: m.group(1) + " " + " AND ".join(conds) + " AND ",
                    cypher,
                    count=1
                )
            else:
                # WHERE 절이 없으면 RETURN 또는 ORDER 이전에 새로 추가
                insert_clause = "WHERE " + " AND ".join(conds) + "\n"
                match_pos = re.search(r"(?i)\b(RETURN|ORDER)\b", cypher)
                if match_pos:
                    pos = match_pos.start()
                    cypher = cypher[:pos] + insert_clause + cypher[pos:] 
                else:
                    cypher += "\n" + insert_clause
        
        return cypher

    def decompose(self, original_question: str, base_cypher: str) -> list:
        """
        원본 Cypher 쿼리를 분해하여 조건을 하나씩 제거한 서브쿼리들 생성
        """
        # 전처리 (MATCH 절의 속성 필터를 WHERE 절로 이동)
        refined_cypher = self._match_to_where(base_cypher.strip())
        
        # 프롬프트 템플릿 정의
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("You are an expert Cypher generator."),
            HumanMessagePromptTemplate.from_template(
                "Given this original question:\n"
                "{original_question}\n"
                "Following Cypher was generated but could not find appropriate results:\n"
                "{refined_cypher}\n\n"
                "Generate valid Cypher sub-queries by removing exactly one filtering condition in each.\n"
                "IMPORTANT RULES:\n"
                "- Keep the exact same MATCH pattern structure\n" 
                "- Only remove conditions from WHERE clause, never modify MATCH clause\n"
                "- When removing a condition about node property (e.g. p.`상품명`), keep it as p.`상품명`\n"
                "- When removing a condition about different node property (e.g. h.`혜택명`), keep it as h.`혜택명`\n"
                "- Do NOT change node aliases or property references\n"
                "- Do NOT move properties between different nodes\n\n"
                "Example:\n"
                "Original: MATCH (p:`요금제`)-[:`제공혜택`]->(h:`혜택`) WHERE p.`상품명` CONTAINS '청년' AND h.`혜택명` CONTAINS 'VIP' RETURN p, h\n"
                "Correct decomposition:\n"
                "1. MATCH (p:`요금제`)-[:`제공혜택`]->(h:`혜택`) WHERE p.`상품명` CONTAINS '청년' RETURN p, h\n"
                "2. MATCH (p:`요금제`)-[:`제공혜택`]->(h:`혜택`) WHERE h.`혜택명` CONTAINS 'VIP' RETURN p, h\n\n"
                "Return ONLY a JSON array of the Cypher strings:\n"
                "[\n"
                "   \"MATCH ... WHERE remaining_condition RETURN ...\",\n"
                "   \"MATCH ... WHERE other_remaining_condition RETURN ...\"\n"
                "]\n"
            )
        ])
        
        try:
            # LLM 파이프라인 실행
            pipeline = prompt | self.llm_model
            raw_output = pipeline.invoke({
                "original_question": original_question, 
                "refined_cypher": refined_cypher
            })
            
            # JSON 문자열 파싱
            content = raw_output.content.strip()
            # content에서 json 부분만 추출 (```json\n과\n``` 제거)
            json_string = content.replace("```json", "").replace("```", "").strip()
            
            sub_queries = json.loads(json_string)
            return sub_queries if isinstance(sub_queries, list) else []
            
        except json.JSONDecodeError as e:
            print(f"JSON 디코딩 에러: {e}")
            return []
        except Exception as e:
            print(f"CypherDecomposer 오류: {e}")
            return []