# src/app/tools/prod_meta_tools.py

import asyncio
import json
import logging
import os
from typing import Dict

from fastapi import HTTPException
from langchain.prompts import (
    PromptTemplate, ChatPromptTemplate, 
    SystemMessagePromptTemplate, HumanMessagePromptTemplate
)
from langchain.tools import tool
from langchain_neo4j import GraphCypherQAChain
from langchain_openai import ChatOpenAI
# from langchain_ollama import ChatOllama # 사외망에서 테스트 실행시에
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chains.llm import LLMChain

from .cypher_validation import CustomNeo4jGraph, CypherValidator, ChainedCorrector
from .CypherAnalyzer import CypherDecomposer


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

def determine_question(query: str, llm_model: ChatOpenAI, plan_list: list):
    """
    Determine whether the question contains plan name or not
    """
    
    response_schemas = [
        ResponseSchema(name="mentioned", description="Plans specified in the question (refer to the plan list below)."),
        ResponseSchema(name="candidates", description="List of plans that are likely mentioned in the question (the top 5 most probable plans). If none, return an empty list.")
    ]
    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()

    # 프롬프트 템플릿 정의
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("Should answer in JSON format"),
        HumanMessagePromptTemplate.from_template(
            "Determine whether the question is asking about a specific plan or about finding a plan that meets certain conditions.\n"
            "If it’s the former, select the specified plan from the plan list below. Otherwise, do not select any plans.\n"
            "{format_instructions}\n"
            "Plan list:\n"
            "{plan_list}\n"
            "User's question:\n"
            "\"{query}\""
        ),
    ])
    
    pipeline = prompt | llm_model
    raw_output = pipeline.invoke({"format_instructions": format_instructions, "plan_list": plan_list, "query": query})
        
    result = output_parser.parse(raw_output.content)
    
    return result


@tool(parse_docstring=True)
def prod_meta_search(query: str):
    """
    Provides detailed search results for SKTelecom's mobile plans, additional services, and benefitial offers.
    Takes a user query, generates a Cypher query, and returns the result from the graph database in text foramt.

    Args:
        query (str): User's query

    Returns:
        dict: Cypher query and search results in text format
    """
    
    try:
        graph = CustomNeo4jGraph(
            url = "bolt://neo4j-gds-apoc-n10s:7687",
            username="neo4j",
            password="neo4jpassword",
            enhanced_schema=True,
            sanitize=True
        )
        
        llm_model = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
        )
        
        # llm_model = ChatOllama(
        #     base_url="http://host.docker.internal:11434",
        #     # model="tomasonjo/llama3-text2cypher-demo:latest",
        #     model="qwen3:8b",
        # )
        
        # Step 1 - 질문을 하나의 cypher로 처리 시도
        chain = GraphCypherQAChain.from_llm(
            llm_model,
            cypher_prompt=CYPHER_GENERATION_PROMPT,
            graph=graph,
            verbose=True,
            allow_dangerous_requests=True,
            exclude_types=[],
            return_intermediate_steps=True,
            return_direct=True,
            validate_cypher=True,
            # disabled_params={"parallel_tool_calls": None}
        )
        
        # # Query pre-validation
        # # 기존(기본) corrector 보존
        # default_corrector = chain.cypher_query_corrector 
        # custum_corrector = CypherValidator(graph=graph)
        
        # chain.cypher_query_corrector = ChainedCorrector(
        #     first=custum_corrector,
        #     second=default_corrector
        # )
        
        # 쿼리 실행
        chain_result = chain.invoke({"query": query})
        
        # Cypher 쿼리와 결과 추출
        cypher = chain_result["intermediate_steps"][0]["query"]
        search_res = chain_result["result"]
        
        if search_res != []:
            print("####### Case 1 ######", flush=True)
            # search_res_json = json.dumps(search_res, ensure_ascii=False, indent=2)
            search_res_json = search_res
            return {
                "case": "1",
                "cypher": [cypher],
                "result": [search_res_json]
            }
            
        # Step 2 - step 1에서 결과가 없는 경우
        
        # 요금제 노드의 상품명 속성값 모두를 리스트로 만들어서 불러오기
        cypher_query = "MATCH (p:`요금제`) RETURN COLLECT(p.`상품명`) AS `상품명`"
        plan_list = ", ".join(graph.query(cypher_query)[0]["상품명"])
        
        # LangChain으로 LLM 연결해서 질문 유형 분석
        # output sample
        # mentioned: 질문에서 언급된 요금제, candiates: (참고자료) 질문에서 언급된 요금제로 추측되는 요금제 5개의 리스트 (mentioned의 요금제도 포함되어 있을 수 있음)
        # {'mentioned': '0 청년 59', 'candidates': ['0 청년 59 100GB업', '0 청년 59 36GB업', '0 청년 59 60GB업', '0 청년 59 15GB업', '0 청년 59']}
        determine_res = determine_question(query, llm_model, plan_list)
        
        print("##### Question type determining")
        print(determine_res, flush=True)
        
        if determine_res["mentioned"] != "":
            print("####### Case 2-1 ######", flush=True)
            # 요금제를 지정한 질문
            # - 상품 조회과 1-hop으로 연결된 노드들 조회 및 리턴
            # - 상품은 있는데 추가 조건에 부합하는 특정 혜택이나 부가서비스는 없다면 해당 취지로 답변을 생성 (메인 에이전트에서 판단)
            target_plan = determine_res["mentioned"] # 사용자가 언급한 요금제
            # target_plan으로부터 1-hop 떨어진 모든 노드와 속성을 가져옴
            # cypher = f"""MATCH (p:`요금제` {{`상품명`: '{target_plan}'}}) RETURN p {{ .*, connections: [(p)-[r]-(n) | n {{ .*, relType: type(r), relProps: properties(r) }}]}}"""
            # cypher = f"MATCH (p:`요금제` {{`상품명`: '{target_plan}'}}) OPTIONAL MATCH (p)-[r]-(n) RETURN p, COLLECT(DISTINCT r) AS relationships, COLLECT(DISTINCT n) AS neighbors"""
            cypher = f"""MATCH (p:`요금제`)
WHERE p.`상품명` = '{target_plan}'
OPTIONAL MATCH (p)-[r]-(n)
WITH p, collect({{
    relationship: {{
        type: type(r),
        properties: properties(r),
        direction: CASE WHEN startNode(r) = p THEN '->' ELSE '<-' END
    }},
    node: {{
        labels: labels(n),
        properties: properties(n)
    }}
}}) AS neighbors
RETURN [{{
    p: {{
        labels: labels(p),
        properties: properties(p)
    }},
    neighbors: neighbors
}}] AS result"""
            # cypher 결과 가져와서 리턴
            result = graph.query(cypher)
            # search_res_json = json.dumps(result, ensure_ascii=False, indent=2)
            search_res_json = result
            
            return {
                "case": "2-1",
                "cypher": [cypher],
                "result": [search_res_json]
            }
        else:
            print("####### Case 2-2 ######", flush=True)
            # 요금제를 지정하지 않은 질문
            # 일단 기존 로직을 그대로 따르게 하고, 추후에 아래 아이디어를 참고해서 개선
            # - 각 조건이 어떤 속성, 관계를 참조해야 하는지 확인
            #   - 프롬프트에서 주어진 schema로부터 추론하도록 함 (현재 방법)
            #   - 생성된 cypher를 실행해서 결과가 없으면
            #   - 속성, 관계 필터 등을 기준으로 2개 이상의 cypher로 나눠서 시도
            #   - 그래도 없으면 그런 조건으로는 검색이 불가능하다고 답변 OR 속성, 관계를 줄여서 답이 나오면 조건을 모두 만족하는 것은 없지만 이런 것은 있다고 답변
            decomposer = CypherDecomposer(llm_model=llm_model)

            sub_queries = decomposer.decompose(base_cypher=cypher, original_question=query)
            print(sub_queries)
            # sub_queries에 있는 cypher들을 각각 실행해보고, 가장 리턴값의 갯수가 적은 것 하나를 최종 리턴
            cypher_results = []
            for sub_cypher in sub_queries:
                result = graph.query(sub_cypher)
                print(f"### cypher: {" ".join(sub_cypher.split("\n"))}: {len(result)}", flush=True)
                cypher_results.append(result)
            
            return {
                "case": "2-2",
                "cypher": sub_queries,
                "reulst": cypher_results
            }
        
    except Exception as E:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(E)}")
    
    