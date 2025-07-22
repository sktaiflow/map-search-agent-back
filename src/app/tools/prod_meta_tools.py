# src/app/tools/prod_meta_tools.py

import json
import logging
import os
from typing import Dict

from fastapi import HTTPException
from langchain.prompts import PromptTemplate
from langchain.tools import tool
from langchain_neo4j import GraphCypherQAChain
from langchain_openai import ChatOpenAI

# --- ✨ [통합] 팀원의 검증 로직과 커스텀 그래프 클래스를 import 합니다. ---
from .cypher_validation import ChainedCorrector, CustomNeo4jGraph, CypherValidator

logger = logging.getLogger(__name__)

# --- ✨ [통합] 팀원의 매우 상세한 프롬프트를 그대로 채택합니다. ---
CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided in the schema.
Korean terms should be surrounded by backticks (``).

Schema:
{schema}

Domain mapping and other rules:
- For 기본제공데이터용량 (data limit), 문자제공량 (sms limit), 음성통화제공량 (voice limit) and other similar numeric fields about capacity, treat the term 무제한 (unlimited) as the value 99999. Do not apply this rule to price fields.
- For questions about cheap or expensive plans, sort by the value of 월정액 (monthly price).
- For search keywords, prefer a single noun split by a space. For example, use "넷플릭스" instead of "넷플릭스 할인".
- For comparing products, generate a Cypher query that retrieves all products to be compared, and then compare the results.

For age-related queries, generate WHERE clause based on the following examples:
- Plans only for 18 years old -> 가입가능최대나이 = 18 AND 가입가능최소나이 = 18
- Plans for 18 years old -> 가입가능최대나이 >= 18 AND 가입가능최소나이 <= 18
- Plans only for 18 years old and above -> 가입가능최대나이 >= 18 AND 가입가능최소나이 <= 18
- Plans only for 18 years old and below -> 가입가능최대나이 <= 18 AND 가입가능최소나이 <= 18
- Plans only for younger than 13 years old -> 가입가능최대나이 < 13 AND 가입가능최소나이 < 13

For querying list properties, do not use the CONTAINS operator directly on the array itself.
Instead, use one of the following methods depending on the query intent:
- To check for exact inclusion of a value: 'value' IN node.array_property
- To check if any element partially matches a condition (e.g., substring): ANY(item IN node.array_property WHERE item CONTAINS 'value')
- To check if all elements satisfy a condition: ALL(item IN node.array_property WHERE item CONTAINS 'value')

Example:
- 데이터 무제한이고 10만원 미만인 요금제 중 만40세인 사람이 사용할 수 있는 요금제 알려줘 -> MATCH (p:`요금제`)-[:제공]->(d:`데이터용량`) MATCH (p)-[:`가입조건`]-(c:`가입조건`) WHERE d.`기본제공데이터용량` = 99999 AND p.`월정액` < 100000 AND c.`가입가능최대나이` >= 40 AND c.`가입가능최소나이` <= 40 RETURN p
- 39,000원 요금제 데이터 무제한인가요 -> MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE p.`월정액` = 39000 RETURN p, d
- 데이터 무제한, 통화 무제한 요금제 알려주세요 -> MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) MATCH (p:`요금제`)-[:`제공`]->(c:`음성통화`) WHERE d.`기본제공데이터용량` = 99999 AND c.`음성통화제공량` = 99999 RETURN p, d, c

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.
Include the nodes and properties related to the question in the result.

The question is:
{question}"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

@tool(parse_docstring=True)
def prod_meta_search(query: str) -> Dict:
    """
    Provides detailed search results for SKTelecom's mobile plans, additional services, and benefitial offers.
    Takes a user query, generates a Cypher query, and returns the result from the graph database in text format.

    Args:
        query (str): User's query

    Returns:
        dict: A dictionary containing the generated Cypher query and the search results.
    """
    logger.info(f"Neo4j prod_meta_search 시작. 쿼리: '{query}'")
    try:
        # --- ✨ [통합] CustomNeo4jGraph를 사용하여 스키마 검증 준비 ---
        graph = CustomNeo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
            enhanced_schema=True,
            sanitize=True,
        )

        # LangChain 체인 초기화
        chain = GraphCypherQAChain.from_llm(
            ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
                streaming=False, # .invoke() 사용 시 False 권장
                temperature=0,
            ),
            cypher_prompt=CYPHER_GENERATION_PROMPT,
            graph=graph,
            verbose=True,
            allow_dangerous_requests=True,
            return_intermediate_steps=True,
            return_direct=True, # DB 결과만 직접 반환 (자연어 생성 X)
            validate_cypher=True,
        )

        # --- ✨ [통합] 팀원의 커스텀 Cypher 유효성 검증 로직 활성화 ---
        # 1. LangChain의 기본 쿼리 수정기(corrector)를 보존합니다.
        default_corrector = chain.cypher_query_corrector
        # 2. 우리만의 커스텀 검증기(validator)를 생성합니다.
        custom_validator = CypherValidator(graph=graph)
        # 3. 두 개를 ChainedCorrector로 연결하여, 우리 것 먼저 실행 후 기본 것을 실행하도록 설정합니다.
        chain.cypher_query_corrector = ChainedCorrector(
            first=custom_validator,
            second=default_corrector
        )

        # 쿼리 실행
        chain_result = chain.invoke({"query": query})
        logger.info(f"Chain result: {chain_result}")

        # 결과 추출
        cypher_query = chain_result.get("intermediate_steps", [{}])[0].get("query", "Cypher 쿼리 생성 실패")
        db_result = chain_result.get("result", []) # 결과가 없을 경우 빈 리스트

        logger.info(f"생성된 Cypher 쿼리:\n---\n{cypher_query}\n---")
        logger.info(f"데이터베이스 실행 결과: {db_result}")

        # --- ✨ [통합] 에이전트 시스템에 맞는 일관된 반환 형식으로 정리 ---
        if not db_result:
            return {
                "error": "No results found from the database.",
                "generated_cypher": cypher_query,
                "result_metadata": {
                    "validated": False,
                    "notes": "The generated Cypher query returned no results. The query might be incorrect or the data may not exist."
                }
            }

        return {
            "cypher": cypher_query,
            "result": json.dumps(db_result, ensure_ascii=False, indent=2), # 결과를 JSON 문자열로 변환
            "result_metadata": { "validated": True }
        }

    except Exception as e:
        import traceback
        logger.error(f"prod_meta_search 실행 중 에러 발생: {e}")
        traceback.print_exc()
        # 에이전트가 에러를 처리할 수 있도록 dict 형태로 반환
        return {
            "error": str(e),
            "result_metadata": {
                "validated": False,
                "exception": True
            }
        }