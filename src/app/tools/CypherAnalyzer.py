import re
from langchain_openai import ChatOpenAI
from langchain_neo4j import GraphCypherQAChain
from langchain.chains.llm import LLMChain
from .cypher_validation import CustomNeo4jGraph
import json
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate
) 

class CypherDecomposer:
    def __init__(self, llm_model = ChatOpenAI):
        self.llm_model = llm_model
    
    def _match_to_where(self, cypher: str):
        """
        MATCH 절의 속성값 조건을 WHERE 절로 옮기기
        """
        conds = []
        # MATCH 절에서 alias와 속성 블록을 찾아 조건으로 변환
        for alias, props in re.findall(r"\((\w+)[^{}]*\{([^}]+)\}\)", cypher):
            for part in props.split(","):
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
                insert_clause = "WHERE " +  " AND ".join(conds) + "\n"
                match_pos = re.search(r"(?i)\b(RETURN|ORDER)\b", cypher)
                if match_pos:
                    pos = match_pos.start()
                    cypher = cypher[:pos] + insert_clause + cypher[pos:] 
                else:
                    cypher += "\n" + insert_clause
            
        return cypher

    def decompose(self, original_question, base_cypher):
        # 전처리 (MATCH 절의 속성 필터를 WHERE 절로 이동)
        refined_cypher = self._match_to_where(base_cypher.strip())
        
        # 프롬프트 템플릿 정의
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("You are an expert Cypher generator."),
            HumanMessagePromptTemplate.from_template(
                "Given this original question:\n"
                "{original_question}\n"
                "Following Cypher was generated but could not find appropriate results:"
                "{refined_cypher}\n"
                "Generate valid Cypher sub-queries by removing exactly one filtering condition in each.\n"
                "- Keep the rest of the query structure (MATCH, RETURN, etc.) unchanged.\n"
                # "- If there’s only one condition, generate no more than one sub-query by removing it.\n"
                "- Return ONLY a JSON array of the Cypher strings, e.g.:\n"
                "[\n"
                "   \"MATCH ... WHERE cond2 AND cond3 RETURN ...\",\n"
                "   \"MATCH ... WHERE cond1 AND cond3 RETURN ...\"\n"
                "]\n"
            )
        ])
        
        pipeline = prompt | self.llm_model
        raw_output = pipeline.invoke({"original_question": original_question, "refined_cypher": refined_cypher})
        # JSON 문자열 파싱
        content = raw_output.content.strip()
        # content에서 json 부분만 추출 (```json\n과\n``` 제거)
        json_string = content.replace("```json", "").replace("```", "").strip()
        try:
            sub_queries = json.loads(json_string)
        except json.JSONDecodeError as e:
            print(f"JSON 디코딩 에러: {e}")
            return []
        
        return sub_queries

# 사용 예
if __name__ == "__main__":    
    example_question = "현재 운영되고 있는 요금제 중에 데이터용량이 30기가 정도에 데이터 리필 쿠폰을 선물할 수 있는 요금제가 있어?"
    example_cypher = """
MATCH (p:`요금제` {`운영상태`:'운영'})-[:`제공`]->(d:`데이터용량`)
MATCH (d:`데이터용량` {`데이터리필쿠폰선물가능여부`: 'Y'})
WHERE d.`기본제공데이터용량` = 30 
ORDER BY d.`기본제공데이터용량` ASC LIMIT 3 
RETURN p, d
    """
    
    decomposer = CypherDecomposer(ChatOpenAI(
            model="gpt-4o-mini",
            # openai_api_key="", # 실행시 주석 풀고 API KEY 추가 필요
            openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
        ))
    print(decomposer.decompose(example_question, example_cypher))