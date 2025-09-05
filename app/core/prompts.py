from string import Template
from langchain_core.prompts.prompt import PromptTemplate


# TODO 이렇게 쓰면 OPENAI 객체 tool calling을 전혀 이용안하는 방식입니다...
PLANNING_TEMPLATE = """
    당신은 LangGraph 시스템에서 '계획 수립'을 담당하는 AI입니다.
    아래의 사용자 질문을 바탕으로, 순차적 또는 병렬 실행이 필요한 작업 목록을 JSON 형식으로 작성하세요. 
    
    사용자 id: 
    {user_id}

    아웃풋 포멧:
    {format_instructions}

    도구 목록:
    {tool_list_json}

    각 작업에는 'mode' 필드를 포함하세요:
    - "sequential": 이전 step이 끝난 후 실행해야 함
    - "parallel": 병렬로 실행 가능함

    각 도구는 필요 시 다음 인자를 갖습니다:
    - get_service_info, get_subscribed_products → {{ "svc_mgmt_num": "7022044239" }}
    - prod_meta_search → {{ "query": "..." }}

    출력 예시:
    {{
    "plan": [
        {{
        "step": 1,
        "tool": "get_service_info",
        "reason": "가입 정보 확인",
        "mode": "sequential"
        }},
        {{
        "step": 2,
        "tool": "prod_meta_search",
        "reason": "상품 조회",
        "args": {{ "query": "무제한 요금제" }},
        "mode": "parallel"
        }}
    ]
}}
"""

INSIGHTS_TEMPLATE = """
당신은 사용자의 모바일 상품 검색 결과를 분석하여 가성비와 사용자 의도를 고려한 적절한 답변을 제공하는 AI입니다.
사용자 질의: {user_query}
검색 결과: {search_results}
실행 성과: {execution_summary}
위 정보를 바탕으로 사용자에게 도움이 되는 인사이트를 제공하세요:
- 가성비 측면에서의 추천사항
- 사용자 의도에 맞는 상품 선택 가이드
- 주요 특징과 장단점 분석
- 실질적인 사용 조건이나 제약사항
200자 이내로 간결하고 실용적인 답변을 작성하세요.
"""

INSIGHTS_PROMPT = PromptTemplate(
    template=INSIGHTS_TEMPLATE,
    input_variables=["user_query", "search_results", "execution_summary"],
)

SUMMARY_TEMPLATE = """
당신은 검색 결과의 주요 특징과 제한사항을 요약하는 AI입니다.
사용자 질의: {user_query}
검색 결과: {search_results}
실행 통계: {execution_stats}
위 정보를 바탕으로 검색 결과의 주요 특징과 제한사항을 요약하세요:
- 검색된 상품의 주요 특징
- 검색 범위와 조건
- 결과의 한계나 제약사항
- 추가 검색이 필요한 경우의 가이드
150자 이내로 명확하고 구체적인 요약을 작성하세요.
"""

REASONING_TEMPLATE = """
당신은 검색 과정의 추론 근거와 실행 과정을 설명하는 AI입니다.
사용자 질의: {user_query}
검색 케이스: {search_case}
실행 단계: {execution_steps}
재시도 정보: {retry_info}
위 정보를 바탕으로 추론 과정의 근거를 설명하세요:
- 선택된 검색 케이스의 이유
- 주요 실행 단계와 그 순서
- 재시도가 발생한 경우 그 이유와 결과
- 최종 결과에 도달한 논리적 과정
200자 이내로 논리적이고 투명한 설명을 작성하세요.
"""

CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
    Instructions:
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided in the schema.
    Korean terms should be surrounded by backticks (``).

    Schema:
    {schema}

    fewshot examples:
    {fewshot_examples}

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
    - "Find one unlimited data plan" -> "MATCH (p:`요금제`) WHERE p.`기본제공데이터용량` = 99999 RETURN p LIMIT 1"
    - "Find discount benefits for 65 and above" -> "MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최소나이` >= 65 RETURN p, c"

    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.
    Include the nodes and properties related to the question in the result.

    The question is:
    {question}
"""
# PromptTemplate 객체로 생성
PLANNING_PROMPT = PromptTemplate(
    template=PLANNING_TEMPLATE, input_variables=["user_id", "format_instructions", "tool_list_json"]
)
REASONING_PROMPT = PromptTemplate(
    template=REASONING_TEMPLATE,
    input_variables=["user_query", "search_case", "execution_steps", "retry_info"],
)

SUMMARY_PROMPT = PromptTemplate(
    template=SUMMARY_TEMPLATE, input_variables=["user_query", "search_results", "execution_stats"]
)

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question", "fewshot_examples"], template=CYPHER_GENERATION_TEMPLATE
)
