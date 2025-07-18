import json
import logging

from fastapi import HTTPException
from langchain.prompts import PromptTemplate
from langchain.tools import tool
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_openai import ChatOpenAI

from src.app.agents.utils import call_smartbee

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
    - "Find plans that are only available for under 18" -> "MATCH (p:`요금제`) WHERE p.`가입가능최대나이` < 18 AND p.`가입가능최소나이` < 18 RETURN p"
    - "Compare 5GX 프리미엄 plan with other plans that have similar price" -> "MATCH (p:`요금제` {{`상품명`: '5GX 프리미엄'}}) WITH p, p.`월정액` AS reference_price  MATCH (other:`요금제`) WHERE ABS(other.`월정액` - reference_price) <= reference_price * 0.1 RETURN p AS `기준상품`, other AS `유사상품` ORDER BY ABS(other.`월정액` - reference_price)"
    - "Find one unlimited data plan" -> "MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` = 99999 RETURN p LIMIT 1"
    - "Find discount benefits for 65 and above" -> "MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최소나이` >= 65 RETURN p, c"

    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.
    Include the nodes and properties related to the question in the result.

    The question is:
    {question}
"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

@tool(parse_docstring=True)
def prod_meta_search(query: str):
    graph = Neo4jGraph(
        url="bolt://neo4j-gds-apoc-n10s:7687",
        username="neo4j",
        password="neo4jpassword",
        enhanced_schema=True,
        sanitize=True,
    )

    ### 이걸 다시 짜서 
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

        # Validation prompt: is the result valid and relevant?
        validation_prompt = f"""
            다음은 사용자의 질문에 대해 생성된 Cypher 쿼리와 결과입니다.
            이 쿼리와 결과가 적절한지 판단하고, 문제 있다면 개선된 Cypher를 제안하세요.

            - 타당하다면: "정상" 이라고만 답변하세요.
            - 타당하지 않다면: 개선된 쿼리를 다음 형식으로 반환하세요:
            {{"cypher": "MATCH ..."}}

            질문: {query}

            생성된 쿼리:
            {generated_cypher}

            결과:
            {result}
        """

        validation_response = call_smartbee(
            messages=[HumanMessage(content=validation_prompt)],
            system_message="당신은 Cypher 쿼리 품질 검토자입니다.",
            tools=None,
            expect_json=False
        ).content.strip("```").strip()

        if validation_response == "정상":
            return {
                "cypher": generated_cypher,
                "result": result,
                "result_metadata": {"validated": True, "repaired": False}
            }

        # LLM이 개선 쿼리를 반환한 경우
        try:
            parsed = json.loads(validation_response)
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
                    "error": f"LLM 응답 파싱 실패: {str(e)}"
                }
            }

        # validation_response가 JSON도 아니고 "정상"도 아닌 경우
        return {
            "cypher": generated_cypher,
            "result": result,
            "result_metadata": {
                "validated": False,
                "repaired": False,
                "llm_response": validation_response
            }
        }

    except Exception as e:
        return {"error": str(e)}