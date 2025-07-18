import json
import logging

from langchain.prompts import PromptTemplate
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_openai import ChatOpenAI

from src.app.agents.utils import call_smartbee

logger = logging.getLogger(__name__)

CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
    (기존 템플릿 생략 – 그대로 유지)
    The question is:
    {question}
"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

@tool(parse_docstring=True)
def prod_meta_search(query: str) -> dict:
    graph = Neo4jGraph(
        url="bolt://neo4j-gds-apoc-n10s:7687",
        username="neo4j",
        password="neo4jpassword",
        enhanced_schema=True,
        sanitize=True,
    )

    chain = GraphCypherQAChain.from_llm(
        ChatOpenAI(
            model="gpt-4o",
            openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
            temperature=0,
            streaming=True,
        ),
        cypher_prompt=CYPHER_GENERATION_PROMPT,
        graph=graph,
        return_intermediate_steps=True,
        validate_cypher=True,
    )

    try:
        result = chain.run(query)
        generated_cypher = chain.intermediate_steps.get("generated_cypher", "")
        is_llm_response = isinstance(result, str) and "결과가 없습니다" in result

        # ✅ Neo4j에서 빈 리스트가 리턴된 경우 (정상이나 데이터 없음)
        if result == []:
            return {
                "cypher": generated_cypher,
                "result": [],
                "result_metadata": {
                    "validated": True,
                    "repaired": False,
                    "empty_result": True,
                    "llm_generated_response": False
                }
            }

        # ❌ 결과는 있는데 의미 없음 → LLM 리페어 시도
        if not result or is_llm_response:
            repair_prompt = f"""
                다음 Cypher 쿼리는 적절한 결과를 반환하지 못했습니다.
                문제를 분석하고 개선된 Cypher 쿼리를 생성하세요.

                질문: {query}
                생성된 쿼리: {generated_cypher}
                결과: {result}
            """
            repair_response = call_smartbee(
                messages=[HumanMessage(content=repair_prompt)],
                system_message="당신은 Cypher 쿼리 리페어 전문가입니다.",
                tools=None,
                expect_json=False
            ).content.strip("```").strip()

            try:
                parsed = json.loads(repair_response)
                if "cypher" in parsed:
                    repaired_cypher = parsed["cypher"]
                    repaired_result = graph.query(repaired_cypher)
                    return {
                        "cypher": repaired_cypher,
                        "result": str(repaired_result),
                        "result_metadata": {
                            "validated": True,
                            "repaired": True,
                            "original_cypher": generated_cypher
                        }
                    }
            except Exception as e:
                return {
                    "cypher": generated_cypher,
                    "result": result,
                    "result_metadata": {
                        "validated": False,
                        "repaired": False,
                        "repair_failed": True,
                        "llm_generated_response": is_llm_response,
                        "error": str(e)
                    }
                }

        return {
            "cypher": generated_cypher,
            "result": result,
            "result_metadata": {
                "validated": True,
                "repaired": False,
                "llm_generated_response": is_llm_response
            }
        }

    except Exception as e:
        return {
            "error": str(e),
            "result_metadata": {
                "validated": False,
                "repaired": False,
                "exception": True
            }
        }