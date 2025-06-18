from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_ollama import ChatOllama
from src.app.agents.utils import call_pe_tool_v2
from fastapi import HTTPException
import re
import json
import logging
from src.app.agents.logging_config import setup_logging

logger = logging.getLogger(__name__)

CYPHER_GENERATION_TEMPLATE_VANILA = """
You are a Cypher expert. Given a question and a schema, create a syntactically correct Cypher query that answers the question.
Do not include any explanation, markdown, or text—just the Cypher query itself.
Limit the number of results to 10.

Domain mapping and other rules:
- "무제한"과 관련있는 값은 전부 99999로 치환하였음
- 나이 제약 사항이 있는 요금제 -> 나이 비교 검색 필요
- 저렴한 요금제 알려줘 -> 가장 낮은 가격 순으로 소팅
- 리스트 타입 검색 시: ANY(item IN node.list_property WHERE item CONTAINS "키워드") 형식 사용
- 검색 키워드는 가능한 띄어쓰기 없는 단일 명사 사용 (예: "웨이브 할인" 보다 "웨이브" 권장)
- 가입 가능한 요금제에 대해 문의시, 유저의 가입 가능한지 여부(productsubscriptioncondition)도 함께 조회

배열(리스트) 검색 관련 문법:
- 배열 내 요소를 검색할 때는 CONTAINS 연산자를 직접 사용하지 말고 다음 방법 중 하나를 사용하세요:
  1. 배열에 특정 값이 정확히 포함되는지 확인: "값" IN node.array_property
  2. 배열 내 일부 요소가 조건을 만족하는지 확인: ANY(item IN node.array_property WHERE item CONTAINS "값")
  3. 배열 내 모든 요소가 조건을 만족하는지 확인: ALL(item IN node.array_property WHERE item CONTAINS "값")

Schema:
{schema}

Question:
{question}
"""

# 제외한 룰 (나중에 쓸지도 몰라서 남겨둠)
# - Do not try to matching 마케팅키워드 (marketing keywords) from the label itself. Must use the properties of the nodes to match keywords. Not "k = 'keyword'". Do "k.`값` CONTAINS 'keyword'.
CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided in the schema.
Korean terms should be surrounded by backticks (``).
Limit the number of results to 10.

Schema:
{schema}

Domain mapping and other rules:
- For 기본제공데이터용량 (data limit), 문자제공량 (sms limit), 음성통화제공량 (voice limit) and other similar numeric fields, treat the term 무제한 (unlimited) as the value 99999. Do not apply this rule to price fields.
- For age-related queries, check whether the given age is within the range defined by 가입가능최소나이 (minimum age) and 가입가능최대나이 (maximum age).
- For questions about cheap or expensive plans, sort by the value of 월정액 (monthly price).
- For finding benefits or offers, focus primarily on the 마케팅키워드 (marketing keywords) properties and 상품설명 (product description) fields.
- To handle list type properties, use following style cypher: ANY(item IN node.list_property WHERE item CONTAINS "keyword")
- For search keywords, prefer single nouns without spaces. For example, use "넷플릭스" instead of "넷플릭스 할인".
- For questions about available plans, also retrieve whether the user is eligible to subscribe by checking the 상품가입조건 (productsubscriptioncondition).
- For comparing products, generate a Cypher query that retrieves all products to be compared, and then compare the results.

For querying list properties, do not use the CONTAINS operator directly on the array itself.
Instead, use one of the following methods depending on the query intent:
- To check for exact inclusion of a value: "value" IN node.array_property
- To check if any element partially matches a condition (e.g., substring): ANY(item IN node.array_property WHERE item CONTAINS "value")
- To check if all elements satisfy a condition: ALL(item IN node.array_property WHERE item CONTAINS "value")

Results should be grouped by 요금제 (mobile plan) and collect other related nodes as a list.
- MATCH (p:`요금제`)-[:`가입해지조건`]->(benefit:`혜택`) WITH p, COLLECT(benefit) AS benefits RETURN p, benefits LIMIT 10

Example:
- "18세 미만만 가입할 수 있는 요금제 알려줘" -> "MATCH (p:`요금제`)-[:`보유`]->(c:`가입조건`) WHERE c.`가입가능최대나이` < 18 AND c.`가입가능최소나이` < 18 RETURN p, c"
- "5GX 프리미엄 요금제와 가격이 비슷한 요금제 비교해줘" -> "MATCH (p:`요금제` {{`상품명`: '5GX 프리미엄'}}) MATCH (p)-[:`요금정보`]->(price) WITH p, price.`월정액` AS reference_price  MATCH (other:`요금제`) MATCH (other)-[:`요금정보`]->(other_price) WHERE ABS(other_price.`월정액` - reference_price) <= reference_price * 0.1 RETURN p AS `기준상품`, other AS `유사상품` ORDER BY ABS(other.`월정액` - reference_price)"
- "데이터 무제한 요금제 하나만 알려줘" -> "MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` = 99999 RETURN p, d LIMIT 1"

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.
If there are keywords used in the cypher, include the nodes related to those keywords in the result.

The question is:
{question}"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

CYPHER_CORRECTION_TEMPLATE = """Task:Re-generate Cypher statement to query a graph database.
Instructions:
The previous Cypher query was inappropriate or did not return any results.
Modify the Cypher query to ensure it returns relevant results based on the provided schema and the user's question.
You can modify the main keywords by removing symbols, split by spaces, or using synonyms.
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided in the schema.
Korean terms should be surrounded by backticks (``).
Limit the number of results to 10.

Schema:
{schema}

Domain mapping and other rules:
- For 기본제공데이터용량 (data limit), 문자기본제공량 (sms limit), 기본음성제공통화량 (voice limit) and similar numeric fields, treat the term 무제한 (unlimited) as the value 99999. Do not apply this rule to price fields.
- For age-related queries, check whether the given age is within the range defined by 최소나이 (minimum age) and 최대나이 (maximum age).
- For questions about cheap or expensive plans, sort by the value of VAT포함월정액 (VAT included monthly price).
- For finding benefits or offers, focus primarily on the 마케팅키워드 (marketing keywords) nodes and 상품설명 (product description) fields.
- To handle list type properties, use following style cypher: ANY(item IN node.list_property WHERE item CONTAINS "keyword")
- For search keywords, prefer single nouns without spaces. For example, use "넷플릭스" instead of "넷플릭스 할인".
- For questions about available plans, also retrieve whether the user is eligible to subscribe by checking the 상품가입조건 (productsubscriptioncondition).
- For comparing products, generate a Cypher query that retrieves all products to be compared, and then compare the results.
- Do not try to matching 마케팅키워드 (marketing keywords) from the label itself. Must use the properties of the nodes to match keywords. Not "k = 'keyword'". Do "k.`값` CONTAINS 'keyword'.

For querying list properties, do not use the CONTAINS operator directly on the array itself.
Instead, use one of the following methods depending on the query intent:
- To check for exact inclusion of a value: "value" IN node.array_property
- To check if any element partially matches a condition (e.g., substring): ANY(item IN node.array_property WHERE item CONTAINS "value")
- To check if all elements satisfy a condition: ALL(item IN node.array_property WHERE item CONTAINS "value")

Results should be grouped by 요금제 (mobile plan) and collect other related nodes as a list.
- MATCH (p:`요금제`)-[:`가입해지조건`]->(benefit:`혜택`) WITH p, COLLECT(benefit) AS benefits RETURN p, benefits LIMIT 10

Example:
- "18세 미만만 가입할 수 있는 요금제 알려줘" -> "MATCH (p:`요금제`)-[:`최대가입가능나이`]->(maxAge:`최대나이`) WHERE maxAge.`값` < 18 RETURN p, maxAge"
- "5GX 프리미엄 요금제와 가격이 비슷한 요금제 비교해줘" -> "MATCH (p:`요금제` {{`상품명`: '5GX 프리미엄'}}) WITH p, p.`VAT포함월정액` AS reference_price MATCH (other:`요금제`) WHERE ABS(other.`VAT포함월정액` - reference_price) <= reference_price * 0.2 RETURN p AS `기준상품`, other AS `유사상품` ORDER BY ABS(other.`VAT포함월정액` - reference_price)"
- "데이터 무제한 요금제 하나만 알려줘" -> "MATCH (p:`요금제`)-[:`기본제공데이터용량`]->(data:`기본제공데이터용량`) WHERE data.`값` = 99999 RETURN p, data LIMIT 1"

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.
If there are keywords used in the cypher, include the nodes related to those keywords in the result.

The inappropriate previous Cypher query was:
{previous_cypher}

The question is:
{question}
"""

CYPHER_CORRECTION_PROMPT = PromptTemplate(
    input_variables=["schema", "question", "previous_cypher"],
    template=CYPHER_CORRECTION_TEMPLATE,
)

CYPHER_QA_TEMPLATE = """You are a product specialist in SK Telecom helps to form nice and human understandable answers in Korean.
The Information part contains the provided information that you must use to construct an answer.
The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
Make the answer sound as a response to the question. Do not mention that you based the result on the given information.
Answer should contains 상품명 (product name), 상품설명 (product description), VAT포함월정액 (monthlyprice), 최대 가입가능 나이 및 최소 가입가능 나이 (minimum age and maximum age).
If there are more than one product, use top 10 products and the result should be a markdown table.
Do not mention that how you can subscribe to the product.
Here is an example:

Question: 데이터 무제한 요금제 하나만 알려줘
Context:'상품설명': '무제한 데이터와 0청년 특화 혜택 외 디즈니 플러스 멤버십을 제공하는 디즈니 플러스 전용 요금제로 SK텔레콤 공식 온라인 채널인 T다이렉트샵에서 만 19세 이상 34세 이하 개인 고객만 가입 가능한 온라인 전용 무약정 요금제', '라인업': '0청년 다이렉트 디즈니+ 요금제', '상품명': '0 청년 다이렉트 69(디즈니+)', 'VAT포함월정액': 69000
Helpful Answer: 데이터 무제한 요금제에는 0 청년 다이렉트 69(디즈니+)가 있고, 해당 요금제의 월정액 요금은 69,000원입니다. 해당 요금제는 무제한 데이터 외에 0청년 특화 혜택과 디즈니 플러스 멤버십을 제공하며, 만 19세 이상 34세 이하 개인 고객만 가입이 가능한 온라인 전용 무약정 요금제입니다.

Follow this example when generating answers.
If the provided information is empty, say that you don't know the answer.
Information:
{context}

Question: {question}
Helpful Answer:"""

CYPHER_QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"], template=CYPHER_QA_TEMPLATE
)


@tool(parse_docstring=True)
def prod_meta_search(query: str):
    """
    Provides detailed search results for SKTelecom's mobile plans, subscription conditions, additional services, roaming options, and benefitial offers.
    Takes a user query, generates a Cypher query, and returns the result from the graph database in text format.

    Args:
        query (str): User's query

    Returns:
        dict: Cypher query and search results in text format
    """
    # import langchain
    # langchain.debug = True  # Enable debug mode for LangChain

    try:
        graph = Neo4jGraph(
            url="bolt://neo4j-gds-apoc-n10s:7687",  # "bolt://localhost:7687",
            username="neo4j",
            password="neo4jpassword",
            enhanced_schema=True,
            sanitize=True,  # 연결 검증
        )

        # LangChain 초기화
        chain = GraphCypherQAChain.from_llm(
            ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key="e97ee307-a791-4e06-ade1-df4b9d032eed",
                openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
                streaming=True,
                temperature=0,
            ),
            # ChatOllama(
            #     base_url="http://host.docker.internal:11434",
            #     model="tomasonjo/llama3-text2cypher-demo:latest",
            #     streaming=True,
            #     temperature=0
            # ),
            cypher_prompt=CYPHER_GENERATION_PROMPT,
            qa_prompt=CYPHER_QA_PROMPT,
            graph=graph,
            verbose=False,
            allow_dangerous_requests=True,
            # exclude_types=[],
            return_intermediate_steps=True,
            return_direct=True,
            validate_cypher=True,
        )

        # 쿼리 실행
        chain_result = chain.invoke({"query": query})
        logger.info(f"Chain result: {chain_result}")

        # Cypher 쿼리와 결과 추출
        cypher = chain_result["intermediate_steps"][0]["query"]
        result_json = json.dumps(chain_result["result"], ensure_ascii=False, indent=2)

        # # 간이 corrector
        # if result_json == "[]":
        #     print(
        #         "No results found, trying to generate Cypher query again.", flush=True
        #     )

        #     chain = GraphCypherQAChain.from_llm(
        #         ChatOpenAI(
        #             model="gpt-4o-mini",
        #             openai_api_key="e97ee307-a791-4e06-ade1-df4b9d032eed",
        #             openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
        #             streaming=True,
        #             temperature=0,
        #         ),
        #         # ChatOllama(
        #         #     base_url="http://host.docker.internal:11434",
        #         #     model="tomasonjo/llama3-text2cypher-demo:latest",
        #         #     streaming=True,
        #         #     temperature=0
        #         # ),
        #         cypher_prompt=CYPHER_CORRECTION_PROMPT,
        #         qa_prompt=CYPHER_QA_PROMPT,
        #         graph=graph,
        #         verbose=False,
        #         allow_dangerous_requests=True,
        #         exclude_types=["DB타입", "카테고리"],
        #         return_intermediate_steps=True,
        #         return_direct=True,
        #         validate_cypher=True,
        #     )

        #     chain_result = chain.invoke({"query": query, "previous_cypher": cypher})
        #     cypher = chain_result["intermediate_steps"][0]["query"]
        #     result_json = json.dumps(
        #         chain_result["result"], ensure_ascii=False, indent=2
        #     )
        #     # print("\n\nresult_json:", result_json, flush=True)

        return cypher, result_json

    except Exception as e:
        import traceback

        traceback.print_exc()  # 서버 로그에 스택 트레이스 출력
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@tool(parse_docstring=True)
def prod_meta_search_vanila(query: str):
    """
    Provides detailed search results for SKTelecom's mobile plans, subscription conditions, additional services, roaming options, and benefitial offers.
    Takes a user query, generates a Cypher query, and returns the result from the graph database in text format.

    Args:
        query (str): User's query

    Returns:
        dict: Cypher query and search results in text format
    """
    graph = Neo4jGraph(
        url="bolt://neo4j-gds-apoc-n10s:7687",  # "bolt://localhost:7687",
        # url="bolt://localhost:7687",
        username="neo4j",
        password="neo4jpassword",
        # enhanced_schema=True,
        sanitize=True,  # 연결 검증
    )
    prompt_str = CYPHER_GENERATION_TEMPLATE_VANILA.format(
        schema=graph.schema, question=query
    )
    cypher_response = call_pe_tool_v2(system_message=prompt_str, messages=[], tools=[])
    # print("cypher_response>>>>", cypher_response)
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
    # print("cypher_query:", cypher)
    # 3. 그래프에서 검색 결과(텍스트)를 반환
    result = graph.query(cypher)
    result_json = json.dumps(result, ensure_ascii=False, indent=2)
    return cypher, result_json
