from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from src.app.agents.utils import call_pe_tool_v2
from fastapi import HTTPException
import re
import json

# CYPHER_GENERATION_TEMPLATE = """
# You are a Cypher expert. Given a question and a schema, create a syntactically correct Cypher query that answers the question.
# Do not include any explanation, markdown, or text—just the Cypher query itself.
# Limit the number of results to 10.

# Domain mapping and other rules:
# - "무제한"과 관련있는 값은 전부 999999로 치환하였음
# - 나이 제약 사항이 있는 요금제 -> 나이 비교 검색 필요
# - 저렴한 요금제 알려줘 -> 가장 낮은 가격 순으로 소팅
# - 리스트 타입 검색 시: ANY(item IN node.list_property WHERE item CONTAINS "키워드") 형식 사용
# - 검색 키워드는 가능한 띄어쓰기 없는 단일 명사 사용 (예: "웨이브 할인" 보다 "웨이브" 권장)
# - 가입 가능한 요금제에 대해 문의시, 유저의 가입 가능한지 여부(productsubscriptioncondition)도 함께 조회

# 배열(리스트) 검색 관련 문법:
# - 배열 내 요소를 검색할 때는 CONTAINS 연산자를 직접 사용하지 말고 다음 방법 중 하나를 사용하세요:
#   1. 배열에 특정 값이 정확히 포함되는지 확인: "값" IN node.array_property
#   2. 배열 내 일부 요소가 조건을 만족하는지 확인: ANY(item IN node.array_property WHERE item CONTAINS "값")
#   3. 배열 내 모든 요소가 조건을 만족하는지 확인: ALL(item IN node.array_property WHERE item CONTAINS "값")

# Schema:
# {schema}

# Question:
# {question}
# """

CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.

Schema:
{schema}

Domain mapping and other rules:
- For numeric fields, treat the term 무제한 (unlimited) as the value 999999.
- For age-related queries, check whether the given age is within the range defined by 최소나이 (minimum age) and 최대나이 (maximum age).
- For questions about cheap or expensive plans, sort by the value of VAT포함월정액 (VAT included monthly price).
- Focus primarily on the 마케팅키워드 (marketing keywords) nodes and 상품설명 (product description) fields when finding keywords.

Example:
- "18세 미만만 가입할 수 있는 요금제 알려줘" -> "MATCH (p:요금제)-[:최대가입가능나이]->(maxAge:최대나이) WHERE maxAge.값 < 18 RETURN p, maxAge"
Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.

The question is:
{question}"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

CYPHER_QA_TEMPLATE = """You are a product specialist in SK Telecom helps to form nice and human understandable answers in Korean.
The Information part contains the provided information that you must use to construct an answer.
The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
You should write your answer based on the 상품명 (product name), 상품설명 (product description), and VAT포함월정액 (monthlyprice) fields, and you can utilize additional fields depending on the question.
Make the answer sound as a response to the question. Do not mention that you based the result on the given information.
If there are more than one product, the result should be a markdown table.
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
    SKT 에서 제공하는 요금제, 요금제 가입조건, 부가서비스, 로밍, 혜택 상품에 대한 상세 검색 결과를 제공합니다.
    유저의 질의를 받아 Cypher 쿼리를 생성하고, 그래프에서 검색 결과(텍스트)를 반환합니다.

    Args:
        query (str): 유저의 질의

    Returns:
        dict: Cypher 쿼리와 텍스트 검색 결과
    """
    try:
        graph = Neo4jGraph(
            url="bolt://neo4j-gds-apoc-n10s:7687",  #"bolt://localhost:7687",
            username="neo4j",
            password="neo4jpassword",
            # enhanced_schema=True,
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
            cypher_prompt=CYPHER_GENERATION_PROMPT,
            qa_prompt=CYPHER_QA_PROMPT,
            graph=graph, 
            verbose=True,
            allow_dangerous_requests=True,
            exclude_types=["DB타입", "카테고리"],
            return_intermediate_steps=True,
            # validate_cypher=True, 
        )

        # 질문 출력
        print("Query:", query)

        # 쿼리 실행
        chain_result = chain.invoke({"query": query})
        # print(f"Intermediate steps: {result['intermediate_steps']}")
        print(f"Final answer: {chain_result['result']}")

        # Cypher 쿼리와 결과 추출
        cypher = chain_result["intermediate_steps"][0]["query"]
        result_json = json.dumps(chain_result["result"], ensure_ascii=False, indent=2)
        return cypher, result_json

        
    except Exception as e:
        import traceback
        traceback.print_exc()  # 서버 로그에 스택 트레이스 출력
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@tool(parse_docstring=True)
def prod_meta_search_vanila(query: str):
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
        # url="bolt://localhost:7687",
        username="neo4j",
        password="neo4jpassword",
        # enhanced_schema=True,
        sanitize=True,  # 연결 검증
    )
    prompt_str = CYPHER_GENERATION_TEMPLATE.format(schema=graph.schema, question=query)
    cypher_response = call_pe_tool_v2(system_message=prompt_str, messages=[], tools=[])
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
