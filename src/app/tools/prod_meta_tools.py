from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_ollama import ChatOllama
import os
from src.app.agents.utils import call_pe_tool_v2
from fastapi import HTTPException
import re
import json
import logging
from typing import Dict, List, Set, Tuple, Callable
from src.app.agents.logging_config import setup_logging
from neo4j import GraphDatabase
from .cypher_validation import ChainedCorrector, CypherValidator, CustomNeo4jGraph
from langchain.globals import set_debug
# set_debug(True)

logger = logging.getLogger(__name__)

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
- 18세 미만만 가입할 수 있는 요금제가 있어? -> MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최대나이` < 18 AND c.`가입가능최소나이` < 18 RETURN p, c
- 5GX 프리미엄 요금제와 비슷한 요금의 요금제 비교해줘 -> "MATCH (p:`요금제` {{`상품명`: '5GX 프리미엄'}}) WITH p, p.`월정액` AS reference_price  MATCH (other:`요금제`) WHERE ABS(other.`월정액` - reference_price) <= reference_price * 0.1 RETURN p AS `기준상품`, other AS `유사상품` ORDER BY ABS(other.`월정액` - reference_price)
- 무제한 데이터 요금제 하나 알려줘 -> MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` = 99999 RETURN p, d LIMIT 1
- 65세 이상이면 요금 할인혜택 없나요 -> MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최소나이` >= 65 OPTIONAL MATCH (p)-[:`제공혜택`]->(h:`혜택`) RETURN p, c, h
- 실버요금제 -> MATCH (p:`요금제`)-[:`연관`]->(c:`개념`) WHERE c.`키워드` = '실버요금제' RETURN p, c
- 내 요금제로 스마트기기 쓸 수 있어? -> MATCH (p:`요금제` {{`상품명`: '5GX 프라임'}})-[:`제공혜택`]->(c:`혜택`) WHERE c.`혜택명` CONTAINS '스마트워치'  OR c.`혜택명` CONTAINS '태블릿' RETURN p, c
- 데이터 무제한이고 10만원 미만인 요금제 중 만40세인 사람이 사용할 수 있는 요금제 알려줘 -> MATCH (p:`요금제`)-[:제공]->(d:`데이터용량`) MATCH (p)-[:`가입조건`]-(c:`가입조건`) WHERE d.`기본제공데이터용량` = 99999 AND p.`월정액` < 100000 AND c.`가입가능최대나이` >= 40 AND c.`가입가능최소나이` <= 40 RETURN p
- 19세이하 요금제 -> MATCH (p:`요금제`)-[:`가입조건`]->(a:`가입조건`) WHERE a.`가입가능최대나이` <= 19 AND a.`가입가능최소나이` <= 19 RETURN p, a
- 데이터를 사용한만큼 금액을 내는 요금제는 없어? -> MATCH (p:`요금제`)-[:`연관`]->(c:`개념`) WHERE c.`키워드` = '종량제요금제' RETURN p, c
- 데이터 30기가면 될 것 같은데 내가 가입가능한 요금제가 뭐가 있을까? -> MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` >= 30 ORDER BY d.`기본제공데이터용량` ASC LIMIT 3 RETURN p, d
- 요금제에 음악 듣기 서비스가 되는 요금제가 있나요 -> MATCH (p:`요금제`)-[]->(n:`개념`) WHERE n.`키워드` CONTAINS '음악듣기요금제' RETURN p, n
- 멤버십 VIP 시켜주는 요금제 중 가장 제공 혜택 개수가 많은 요금제는 뭐야? -> MATCH (p:`요금제`)-[:`제공혜택`]->(h:`혜택`) WHERE h.`혜택명` CONTAINS 'VIP' WITH p MATCH (p)-[:`제공혜택`]->(b:`혜택`) WITH p, COUNT(b) AS b_count ORDER BY b_count DESC RETURN p, b_count
- 우주패스 할인율 제일 크게 주는 요금제가 뭐야? -> MATCH (p:`요금제`)-[:`제공혜택`]->(h:`혜택`) WHERE h.`혜택명` CONTAINS '우주패스' ORDER BY h.`최대할인금액` DESC RETURN p, h LIMIT 1
- 65세 이상 요금 할인 혜택 알려줘 -> MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최소나이` >= 65 OPTIONAL MATCH (p)-[:`제공혜택`]->(h:`혜택`) RETURN p, h
- FLO 제일 싸게 쓰려면 어떻게 해야해? -> MATCH (h:`혜택`) WHERE h.`혜택명` = 'FLO 무료' ORDER BY h.`최대할인금액` DESC LIMIT 1 WITH h MATCH (p:`요금제`)-[]->(h) ORDER BY p.`월정액` ASC RETURN p, h
- 무제한 데이터 혜택 요금제 -> MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` = 99999 RETURN p
- 베이직플러스로 변경 시 T가족모아데이터 이용 가능한가요? -> MATCH (p:요금제)-[r]->(b:혜택) WHERE b.혜택명 = 'T가족모아데이터'  AND p.상품명 = '베이직플러스' RETURN p, r, b
- 39,000원 요금제 데이터 무제한인가요 -> MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE p.`월정액` = 39000 RETURN p, d
- 데이터 무제한, 통화 무제한 요금제 알려주세요 -> MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) MATCH (p:`요금제`)-[:`제공`]->(c:`음성통화`) WHERE d.`기본제공데이터용량` = 99999 AND c.`음성통화제공량` = 99999 RETURN p, d, c
- SKT 표준 요금제도 T끼리 데이터선물 받을 수 있어? -> MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE p.`상품명` CONTAINS '표준' RETURN p, d
- 아이패드 회선 무료 이용 요금제 -> MATCH (p:`요금제`) WHERE ANY(k IN p.`마케팅키워드` WHERE k CONTAINS '태블릿요금무료') RETURN p
- 키즈 요금제에서 MMS 사용료가 있나요? -> MATCH (p:`요금제`)-[:`제공`]->(m:`문자메시지`) WHERE ANY(keyword IN p.`마케팅키워드` WHERE keyword CONTAINS '키즈') RETURN p, m
- 시니어요금제 -> MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최소나이` >= 65 RETURN p, c
- 자녀요금제는어떤것들이있나요? -> MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최대나이` <= 18 RETURN p
- VIP 되려면 0청년 59 요금제 쓰면 돼? -> MATCH (p:`요금제`)-[r:`제공혜택`]->(n:`혜택` {{`혜택명`:'T멤버십 VIP'}}) WHERE p.`상품명` CONTAINS '0 청년' AND p.`상품명` CONTAINS '59' RETURN p, n

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
def prod_meta_search(query: str):
    """
    Provides detailed search results for SKTelecom's mobile plans, additional services, and benefitial offers.
    Takes a user query, generates a Cypher query, and returns the result from the graph database in text format.

    Args:
        query (str): User's query

    Returns:
        dict: Cypher query and search results in text format
    """
    # import langchain
    # langchain.debug = True  # Enable debug mode for LangChain

    try:
        graph = CustomNeo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
            enhanced_schema=True,
            sanitize=True,  # 연결 검증
        )
        
        # # 개념 힌트 추가
        # driver = GraphDatabase.driver("bolt://neo4j-gds-apoc-n10s:7687", auth=("neo4j", "neo4jpassword"))
        
        # concept_query = """
        # MATCH (c:개념)
        # OPTIONAL MATCH (c)-[:연관]->(p:요금제)
        # WITH c, collect(p.상품명) AS plans
        # RETURN c.키워드 AS keyword,
        #     c.설명 AS description,
        #     coalesce(c.CYPHER_TEMPLATE, '') AS CYPHER_TEMPLATE,
        #     plans
        # """
        
        # with driver.session() as session:
        #     result = session.run(concept_query)
        #     concepts_data = [record for record in result]
        
        # driver.close()
        
        # lines = []
        # for rec in concepts_data:
        #     keyword = rec["keyword"]
        #     description = rec["description"]
        #     CYPHER_TEMPLATE = rec["CYPHER_TEMPLATE"]
        #     plans = rec["plans"]

        #     lines.append(f"- concept keyword: {keyword}")
        #     lines.append(f"  - description: {description}")
        #     if CYPHER_TEMPLATE:
        #         lines.append(f"  - cypher example: {CYPHER_TEMPLATE}")
        #     # if plans:
        #     #     lines.append(f"  - related plans: {', '.join(plans)}")
        # hint_block = "\n".join(lines)
        
        # global CYPHER_GENERATION_TEMPLATE
        # CYPHER_GENERATION_TEMPLATE = CYPHER_GENERATION_TEMPLATE.replace("{{hint_block}}", hint_block)
        # print(CYPHER_GENERATION_TEMPLATE, flush=True)

        # LangChain 초기화
        chain = GraphCypherQAChain.from_llm(
            ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
                # streaming=True,
                # temperature=0,
            ),
            # ChatOllama(
            #     base_url="http://host.docker.internal:11434",
            #     model="tomasonjo/llama3-text2cypher-demo:latest",
            #     streaming=True,
            #     temperature=0
            # ),
            cypher_prompt=CYPHER_GENERATION_PROMPT,
            # qa_prompt=CYPHER_QA_PROMPT,
            graph=graph,
            verbose=True,
            allow_dangerous_requests=True,
            exclude_types=[],
            return_intermediate_steps=True,
            return_direct=True,
            validate_cypher=True,
            # disabled_params={"parallel_tool_calls": None}
        )

        # Query pre-validation
        # # 기존(기본) corrector 보존
        # default_corrector = chain.cypher_query_corrector 
        # custum_corrector = CypherValidator(graph=graph)
        
        # chain.cypher_query_corrector = ChainedCorrector(
        #     first=custum_corrector,
        #     second=default_corrector
        # )

        # 쿼리 실행
        chain_result = chain.invoke({"query": query})
        logger.info(f"Chain result: {chain_result}")
        
        # Cypher 쿼리와 결과 추출
        cypher = chain_result["intermediate_steps"][0]["query"]
        result_json = json.dumps(chain_result["result"], ensure_ascii=False, indent=2)

        return cypher, result_json

    except Exception as e:
        import traceback

        traceback.print_exc()  # 서버 로그에 스택 트레이스 출력
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
