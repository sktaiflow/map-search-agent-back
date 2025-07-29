# src/app/tools/prod_meta_tools.py

import asyncio
import json
import logging
import os
from typing import Dict

from fastapi import HTTPException
from langchain.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.tools import tool
from langchain_neo4j import GraphCypherQAChain
from langchain_openai import ChatOpenAI

# from langchain_ollama import ChatOllama # 사외망에서 테스트 실행시에
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chains.llm import LLMChain

from .cypher_validation import CustomNeo4jGraph, CypherValidator, ChainedCorrector
from .CypherAnalyzer import CypherDecomposer
from .vector_retriever import few_shot_retriever


logger = logging.getLogger(__name__)

# For debug
from langchain.globals import set_debug
# set_debug(True)

# --- 동적 Few-shot 프롬프트 템플릿 ---
DYNAMIC_CYPHER_GENERATION_TEMPLATE = """작업: 그래프 데이터베이스 조회를 위한 Cypher 쿼리문을 생성하세요.

지침:
- 제공된 스키마의 관계 타입과 속성만 사용하세요.
- 스키마에 없는 관계 타입이나 속성은 절대 사용하지 마세요.
- 한국어 용어는 백틱(``)으로 감싸주세요.

스키마:
{schema}

도메인 매핑 및 규칙:
- 기본제공데이터용량, 문자제공량, 음성통화제공량 등 용량 관련 숫자 필드에서 '무제한'은 99999 값으로 처리하세요. 단, 가격 필드에는 적용하지 마세요.
- 저렴하거나 비싼 요금제에 대한 질문시 월정액 값을 기준으로 정렬하세요.
- 검색 키워드는 공백으로 구분된 단일 명사를 선호하세요. 예: "넷플릭스 할인" 대신 "넷플릭스"
- 상품 비교 시 비교할 모든 상품을 조회하는 쿼리를 생성한 후 결과를 비교하세요.

특정 요금제명 검색 우선순위:
특정 요금제명으로 검색할 때는 다음 우선순위를 따르세요:
1. 첫 번째 우선순위: 상품명에서 CONTAINS로 검색
2. 두 번째 우선순위: 라인업 필드에서 검색 (있는 경우)
3. 마지막 우선순위: 마케팅키워드에서 검색

특정 요금제명 검색 예시:
- "5GX 프리미엄 알려줘" → WHERE p.`상품명` CONTAINS '5GX 프리미엄'
- "티플랜 요금제" → WHERE p.`상품명` CONTAINS '티플랜' OR p.`라인업` CONTAINS '티플랜' OR ANY(keyword IN p.`마케팅키워드` WHERE keyword CONTAINS '티플랜')
- "0플랜 정보" → WHERE p.`상품명` CONTAINS '0플랜' OR ANY(keyword IN p.`마케팅키워드` WHERE keyword CONTAINS '0플랜')

연령 관련 쿼리는 다음 예시를 기반으로 WHERE 절을 생성하세요:
- 만 18세만 가능한 요금제 → 가입가능최대나이 = 18 AND 가입가능최소나이 = 18
- 만 18세 가입 가능한 요금제 → 가입가능최대나이 >= 18 AND 가입가능최소나이 <= 18
- 만 18세 이상만 가능한 요금제 → 가입가능최대나이 >= 18 AND 가입가능최소나이 <= 18
- 만 18세 이하만 가능한 요금제 → 가입가능최대나이 <= 18 AND 가입가능최소나이 <= 18
- 만 13세 미만만 가능한 요금제 → 가입가능최대나이 < 13 AND 가입가능최소나이 < 13

배열 속성 쿼리 시 CONTAINS 연산자를 배열에 직접 사용하지 마세요.
대신 쿼리 의도에 따라 다음 방법 중 하나를 사용하세요:
- 정확한 값 포함 확인: 'value' IN node.array_property
- 부분 일치 조건 확인: ANY(item IN node.array_property WHERE item CONTAINS 'value')
- 모든 요소가 조건을 만족하는지 확인: ALL(item IN node.array_property WHERE item CONTAINS 'value')

{few_shot_examples}

주의사항:
- 응답에 설명이나 사과는 포함하지 마세요.
- Cypher 쿼리문 생성 외의 다른 질문에는 응답하지 마세요.
- 생성된 Cypher 쿼리문만 포함하세요.
- 질문과 관련된 노드와 속성을 결과에 포함하세요.

질문:
{question}"""


def determine_question(query: str, llm_model: ChatOpenAI, plan_list: list):
    """
    Determine whether the question contains plan name or not
    """

    response_schemas = [
        ResponseSchema(
            name="mentioned",
            description="Plans specified in the question (refer to the plan list below).",
        ),
        ResponseSchema(
            name="candidates",
            description="List of plans that are likely mentioned in the question (the top 5 most probable plans). If none, return an empty list.",
        ),
    ]
    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()

    # 프롬프트 템플릿 정의
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template("Should answer in JSON format"),
            HumanMessagePromptTemplate.from_template(
                "Determine whether the question is asking about a specific plan or about finding a plan that meets certain conditions.\n"
                "If it’s the former, select the specified plan from the plan list below. Otherwise, do not select any plans.\n"
                "{format_instructions}\n"
                "Plan list:\n"
                "{plan_list}\n"
                "User's question:\n"
                '"{query}"'
            ),
        ]
    )

    pipeline = prompt | llm_model
    raw_output = pipeline.invoke(
        {
            "format_instructions": format_instructions,
            "plan_list": plan_list,
            "query": query,
        }
    )

    result = output_parser.parse(raw_output.content)

    return result


@tool(parse_docstring=True)
def prod_meta_search(query: str, original_input: str = None) -> Dict:
    """
    Provides detailed search results for SKTelecom's mobile plans, additional services, and benefitial offers.
    Takes a user query, generates a Cypher query, and returns the result from the graph database in text format.

    Args:
        query (str): Processed query for Neo4j Cypher generation
        original_input (str, optional): Original user input for vector similarity search

    Returns:
        dict: A dictionary containing the generated Cypher query and the search results.
    """
    logger.info(f"Neo4j prod_meta_search 시작. 쿼리: '{query}'")

    try:
        # 1. 유사한 Few-shot 예시 검색 (하이브리드 방식)
        logger.info("벡터 검색으로 Few-shot 예시 찾는 중...")
        
        # 우선 original_input으로 검색 시도
        search_text = original_input if original_input else query
        logger.info(f"벡터 검색 입력: '{search_text}'")
        
        similar_examples = asyncio.run(
            few_shot_retriever.find_similar_examples(
                query=search_text,
                top_k=3,
                min_similarity=0.3
            )
        )
        
        # original_input으로 찾지 못했으면 query로 재시도
        if not similar_examples and original_input and original_input != query:
            logger.info("original_input으로 검색 실패, 정제된 query로 재시도...")
            similar_examples = asyncio.run(
                few_shot_retriever.find_similar_examples(
                    query=query,
                    top_k=3,
                    min_similarity=0.3
                )
            )
        
        # 2. Few-shot 예시를 프롬프트에 추가
        few_shot_text = ""
        if similar_examples:
            few_shot_text = "\nSimilar examples for reference:\n"
            for i, example in enumerate(similar_examples, 1):
                few_shot_text += f"Example {i} (similarity: {example['similarity']:.3f}):\n"
                few_shot_text += f"Question: {example['natural_language']}\n"
                few_shot_text += f"Cypher: {example['cypher_query']}\n\n"
            logger.info(f"Few-shot 예시 {len(similar_examples)}개 찾음")
        else:
            logger.warning("유사한 Few-shot 예시를 찾지 못함")
        
        # 3. CustomNeo4jGraph를 사용하여 스키마 검증 준비
        graph = CustomNeo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
            enhanced_schema=True,
            sanitize=True,
        )
        
        # 4. 동적 프롬프트 생성
        dynamic_prompt = PromptTemplate(
            input_variables=["schema", "question", "few_shot_examples"],
            template=DYNAMIC_CYPHER_GENERATION_TEMPLATE
        )
        
        # 5. LangChain 체인 초기화 (SKT AI Hub 설정)
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
        )

        # llm = ChatOllama(
        #     base_url="http://host.docker.internal:11434",
        #     # model="tomasonjo/llama3-text2cypher-demo:latest",
        #     model="qwen3:8b",
        # )
        
        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            validate_cypher=True,
            cypher_prompt=dynamic_prompt,
            return_intermediate_steps=True,
            allow_dangerous_requests=True,
            return_direct=True, # 자연어 응답 생성 건너뛰기
        )
        
        # 6. Cypher Query Corrector 설정
        # # 기존(기본) corrector 보존
        # default_corrector = chain.cypher_query_corrector 
        # custum_corrector = CypherValidator(graph=graph)
        # chain.cypher_query_corrector = ChainedCorrector(
        #     first=custum_corrector,
        #     second=default_corrector
        # )
        # logger.info("Cypher Query Corrector 설정 완료")

        # 7. 쿼리 실행
        logger.info("LangChain으로 쿼리 실행 중...")
        result = chain.invoke({
            "query": query, 
            "few_shot_examples": few_shot_text
        })
        search_res = result.get("result", [])
        logger.info("################ result #################")
        logger.info(result)
        
        # 8. 결과 처리
        intermediate_steps = result.get('intermediate_steps', [])
        cypher_query = intermediate_steps[0].get('query', '') if intermediate_steps else ''
        refined_cypher = cypher_query[6:].strip() if cypher_query.startswith("cypher") else cypher_query.strip()
        
        # 디버깅: intermediate_steps 출력
        logger.info(f"=== intermediate_steps 디버깅 ===")
        logger.info(f"생성된 Cypher 쿼리:\n{refined_cypher}")
        logger.info(f"사용된 Few-shot 예시 수: {len(similar_examples)}")
        logger.info(f"데이터베이스 실행 결과: {result['result']}")
        
        if search_res != []:
            logger.info("####### Case 1 ######")
            # search_res_json = json.dumps(search_res, ensure_ascii=False, indent=2)
            search_res_json = search_res
            return {
                "case": "1", 
                "cypher": [refined_cypher], 
                "result": "",
                "raw_data": [search_res_json],
                "similar_examples_used": len(similar_examples),
                "few_show_examples": [ex['natural_language'] for ex in similar_examples] if similar_examples else [],
                "result_metadata": {
                    "validated": True,
                    "corrector_used": True,
                    "vector_search_enabled": True
                }
            }

        # 9. (한 번의 Text2Cypher로 결과를 찾지 못한 경우) 질문에 상품명이 포함되어있는지 확인하고 case 2-1, case 2-2로 분기
        # 요금제 노드의 상품명 속성값 모두를 리스트로 만들어서 불러오기
        cypher_query = "MATCH (p:`요금제`) RETURN COLLECT(p.`상품명`) AS `상품명`"
        plan_list = ", ".join(graph.query(cypher_query)[0]["상품명"])

        # LangChain으로 LLM 연결해서 질문 유형 분석
        # output sample
        # mentioned: 질문에서 언급된 요금제, candiates: (참고자료) 질문에서 언급된 요금제로 추측되는 요금제 5개의 리스트 (mentioned의 요금제도 포함되어 있을 수 있음)
        # {'mentioned': '0 청년 59', 'candidates': ['0 청년 59 100GB업', '0 청년 59 36GB업', '0 청년 59 60GB업', '0 청년 59 15GB업', '0 청년 59']}
        determine_res = determine_question(query, llm, plan_list)

        logger.info("##### Question type determining")
        logger.info(determine_res)

        if determine_res["mentioned"] != "":
            logger.info("####### Case 2-1 ######")
            # 요금제를 지정한 질문
            # - 상품 조회과 1-hop으로 연결된 노드들 조회 및 리턴
            # - 상품은 있는데 추가 조건에 부합하는 특정 혜택이나 부가서비스는 없다면 해당 취지로 답변을 생성 (메인 에이전트에서 판단)
            target_plan = determine_res["mentioned"]  # 사용자가 언급한 요금제
            # target_plan으로부터 1-hop 떨어진 모든 노드와 속성을 가져옴
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
                "result": "",
                "raw_data": [search_res_json],
                "similar_examples_used": len(similar_examples),
                "few_show_examples": [ex['natural_language'] for ex in similar_examples] if similar_examples else [],
                "result_metadata": {
                    "validated": True,
                    "corrector_used": True,
                    "vector_search_enabled": True
                }
            }
        else:
            logger.info("####### Case 2-2 ######")
            # 요금제를 지정하지 않은 질문
            # 일단 기존 로직을 그대로 따르게 하고, 추후에 아래 아이디어를 참고해서 개선
            # - 각 조건이 어떤 속성, 관계를 참조해야 하는지 확인
            #   - 프롬프트에서 주어진 schema로부터 추론하도록 함 (현재 방법)
            #   - 생성된 cypher를 실행해서 결과가 없으면
            #   - 속성, 관계 필터 등을 기준으로 2개 이상의 cypher로 나눠서 시도
            #   - 그래도 없으면 그런 조건으로는 검색이 불가능하다고 답변 OR 속성, 관계를 줄여서 답이 나오면 조건을 모두 만족하는 것은 없지만 이런 것은 있다고 답변
            decomposer = CypherDecomposer(llm_model=llm)

            sub_queries = decomposer.decompose(
                base_cypher=refined_cypher, original_question=query
            )
            logger.info(refined_cypher)
            logger.info(sub_queries)
            # sub_queries에 있는 cypher들을 각각 실행해보고, 가장 리턴값의 갯수가 적은 것 하나를 최종 리턴
            cypher_results = []
            for sub_cypher in sub_queries:
                result = graph.query(sub_cypher)
                print(
                    f"### cypher: {" ".join(sub_cypher.split("\n"))}: {len(result)}",
                    flush=True,
                )
                cypher_results.append(result)

            return {
                "case": "2-2", 
                "cypher": sub_queries, 
                "result": "",
                "raw_data": cypher_results,
                "similar_examples_used": len(similar_examples),
                "few_show_examples": [ex['natural_language'] for ex in similar_examples] if similar_examples else [],
                "result_metadata": {
                    "validated": True,
                    "corrector_used": True,
                    "vector_search_enabled": True
                }
            } 
    except Exception as E:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(E)}")
