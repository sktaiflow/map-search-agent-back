# src/app/tools/prod_meta_tools.py

import asyncio
import json
import logging
import os
from typing import Dict

from fastapi import HTTPException
from langchain.prompts import PromptTemplate
from langchain.tools import tool
from langchain_neo4j import GraphCypherQAChain
from langchain_openai import ChatOpenAI

# --- 기존 검증 로직과 벡터 검색 import ---
from .cypher_validation import ChainedCorrector, CustomNeo4jGraph, CypherValidator
from .vector_retriever import few_shot_retriever
from langchain.globals import set_debug
set_debug(True)

logger = logging.getLogger(__name__)

# --- 동적 Few-shot 프롬프트 템플릿 ---
DYNAMIC_CYPHER_GENERATION_TEMPLATE = """Task: Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided in the schema.
Korean terms should be surrounded by backticks (``).

Schema:
{schema}

Domain mapping and other rules:
- For searching a plan itself, find 상품명 (product name), 마케팅키워드 (marketing keyword). 
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

{few_shot_examples}

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.
Include the nodes and properties related to the question in the result.

The question is:
{question}"""

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

        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            validate_cypher=True,
            cypher_prompt=dynamic_prompt,
            return_intermediate_steps=True,
            allow_dangerous_requests=True,
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
        logging.info(result)
        
        # 8. 결과 처리
        intermediate_steps = result.get('intermediate_steps', [])
        cypher_query = intermediate_steps[0].get('query', '') if intermediate_steps else ''
        
        # 디버깅: intermediate_steps 전체 구조 출력
        logger.info(f"=== intermediate_steps 디버깅 ===")
        logger.info(f"intermediate_steps 길이: {len(intermediate_steps)}")
        for i, step in enumerate(intermediate_steps):
            logger.info(f"Step {i}의 키들: {list(step.keys())}")
            for key, value in step.items():
                logger.info(f"  - {key}: {type(value)} ({len(value) if isinstance(value, (list, dict, str)) else 'N/A'})")
                if key in ['context', 'result', 'output'] and isinstance(value, list) and len(value) > 0:
                    logger.info(f"    첫 번째 아이템: {type(value[0])}")
        
        # raw_data 추출 시도 - 모든 step 확인
        raw_data = []
        for step in intermediate_steps:
            potential_data = step.get('context', step.get('result', step.get('output', [])))
            if isinstance(potential_data, list) and len(potential_data) > 0:
                raw_data = potential_data
                break
        
        logger.info(f"생성된 Cypher 쿼리:\n---\n{cypher_query}\n---")
        logger.info(f"사용된 Few-shot 예시 수: {len(similar_examples)}")
        logger.info(f"데이터베이스 실행 결과: {result['result']}")
        logger.info(f"추출된 raw_data 타입: {type(raw_data)}, 길이: {len(raw_data) if isinstance(raw_data, (list, dict, str)) else 'N/A'}")
        
        return {
            "cypher": cypher_query,
            "result": result.get('result', ''),
            "raw_data": raw_data,
            "similar_examples_used": len(similar_examples),
            "few_shot_examples": [ex['natural_language'] for ex in similar_examples] if similar_examples else [],
            "result_metadata": {
                "validated": True,
                "corrector_used": True,
                "vector_search_enabled": True
            }
        }

    except Exception as e:
        logger.exception(f"prod_meta_search 실행 중 에러: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")