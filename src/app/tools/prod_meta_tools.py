from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_neo4j import Neo4jGraph
from src.app.agents.utils import call_pe_tool_v2
import re
import json

CYPHER_GENERATION_TEMPLATE = """
You are a Cypher expert. Given a question and a schema, create a syntactically correct Cypher query that answers the question.
Do not include any explanation, markdown, or text—just the Cypher query itself.
Limit the number of results to 5.

Domain mapping and other rules:
- "무제한"과 관련있는 값은 전부 999999로 치환하였음
- 나이 제약 사항이 있는 요금제 -> 나이 비교 검색 필요
- 저렴한 요금제 알려줘 -> 가장 낮은 가격 순으로 소팅

Schema:
{schema}

Question:
{question}
"""


@tool(parse_docstring=True)
def prod_meta_search(query: str):
    """
    SKT 에서 제공하는 요금제, 부가서비스, 로밍, 혜택 상품에 대한 상세 검색 결과를 제공합니다.
    유저의 질의를 받아 Cypher 쿼리를 생성하고, 그래프에서 검색 결과(텍스트)를 반환합니다.
    최대 5개의 결과만을 반환합니다.

    Args:
        query (str): 유저의 질의

    Returns:
        dict: Cypher 쿼리와 텍스트 검색 결과
    """
    graph = Neo4jGraph(
        url="bolt://neo4j-gds-apoc-n10s:7687",  # "bolt://localhost:7687",
        username="neo4j",
        password="neo4jpassword",
        # enhanced_schema=True,
        sanitize=True,  # 연결 검증
    )
    prompt_str = CYPHER_GENERATION_TEMPLATE.format(schema=graph.schema, question=query)
    cypher_response = call_pe_tool_v2(
        system_message=prompt_str, messages=[], tools=[], model_idx=124252
    )
    print("cypher_response>>>>", cypher_response)
    cypher = cypher_response.content
    # Cypher 쿼리만 추출 (설명, 마크다운, 기타 텍스트 제거)
    # # 1. ```cypher ... ``` 블록이 있으면 그 안만 추출
    # match = re.search(r"```cypher\\s*([\\s\\S]+?)```", cypher, re.IGNORECASE)
    # if match:
    #     cypher_query = match.group(1).strip()
    # else:
    #     # 2. 설명이 있으면 첫 번째 MATCH/RETURN/CREATE 등으로 시작하는 줄부터 끝까지 추출
    #     cypher_lines = []
    #     found = False
    #     for line in cypher.splitlines():
    #         if re.match(r'^(MATCH|RETURN|CREATE|WITH|CALL|MERGE|OPTIONAL|UNWIND|SET|DELETE|DETACH|REMOVE|FOREACH|LOAD|START|USING|ORDER BY|SKIP|LIMIT|UNION|PROFILE|EXPLAIN|CYPHER)\\b', line.strip(), re.IGNORECASE):
    #             found = True
    #         if found:
    #             cypher_lines.append(line)
    #     cypher_query = '\n'.join(cypher_lines).strip()
    #     if not cypher_query:
    #         # fallback: 전체 응답 사용
    #         cypher_query = cypher
    print("cypher_query:", cypher)
    # 3. 그래프에서 검색 결과(텍스트)를 반환
    result = graph.query(cypher)
    result_json = json.dumps(result, ensure_ascii=False, indent=2)
    return cypher, result_json
