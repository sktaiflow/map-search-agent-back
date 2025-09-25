from string import Template
from langchain_core.prompts.prompt import PromptTemplate


# 도구 정보는 OpenAI tool 사양을 통해 주입됩니다.
PLANNING_TEMPLATE = """당신은 LangGraph 시스템에서 '계획 수립'을 담당하는 AI입니다.
사용자의 질의에 답변하기 위해 주어진 도구(tool)를 어떤 순서로 호출할지 계획을 세우고, 그 계획을 JSON 형식의 tool_calls로 출력해야 합니다.
# 지침
- 사용자의 요청을 주의 깊게 읽고, 이번 단계에서 호출해야 할 도구 하나를 선택합니다.
- 호출해야 할 도구가 선택되면, 해당 도구에 어떤 파라미터를 전달할지 결정합니다.
- 제공된 도구의 스키마(name, arguments)를 반드시 그대로 사용합니다.
- 사용자ID(user_id 또는 svcMgmtNum)가 필요한 도구에는 반드시 user_id 값을 그대로 사용하세요.
user_id: {user_id}"""

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

CYPHER_GENERATION_TEMPLATE = """작업: 그래프 데이터베이스 조회를 위한 Cypher 쿼리문을 생성하세요.
지침:
- 제공된 스키마의 관계 타입과 속성만 사용하세요.
- 스키마에 없는 관계 타입이나 속성은 절대 사용하지 마세요.
- 한국어 용어는 백틱(``)으로 감싸주세요.

답변 포멧 (JSON 형식을 따라야함):
{{
    "cypher": "<generated cypher statement>",
    "params": {{"param_name": "value"}},
    "reasoning": "<optional concise reasoning>"
}}
항상 JSON 객체로 응답하세요. 마크다운 펜스는 포함하지 마세요. API 요구사항을 만족시키기 위해 "json"이라는 단어가 이미 여기에 포함되어 있습니다.

스키마:
{schema}

도메인 매핑 및 규칙:
- 기본제공데이터용량, 문자제공량, 음성통화제공량 등 용량 관련 숫자 필드에서 '무제한'은 99999 값으로 처리하세요. 단, 가격 필드에는 적용하지 마세요.
- 저렴하거나 비싼 요금제에 대한 질문시 월정액 값을 기준으로 정렬하세요.
- 검색 키워드는 공백으로 구분된 단일 명사를 선호하세요. 예: "넷플릭스 할인" 대신 "넷플릭스"
- 상품 비교 시 비교할 모든 상품을 조회하는 쿼리를 생성한 후 결과를 비교하세요.
- 질문에 숫자형 필드에 대한 조건이 포함된 경우, 해당 필드를 기준으로 결과를 정렬하도록 ORDER BY 문을 사용하세요.

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

{fewshot_examples}

주의사항:
- 응답에 설명이나 사과는 포함하지 마세요.
- Cypher 쿼리문 생성 외의 다른 질문에는 응답하지 마세요.
- 생성된 Cypher 쿼리문만 포함하세요.
- 질문과 관련된 노드와 속성을 결과에 포함하세요.

질문:
{question}"""

# PromptTemplate 객체로 생성
PLANNING_PROMPT = PromptTemplate(
    template=PLANNING_TEMPLATE,
    input_variables=[
        "user_id",
        # "format_instructions",
    ],
)

REASONING_PROMPT = PromptTemplate(
    template=REASONING_TEMPLATE,
    input_variables=["user_query", "search_case", "execution_steps", "retry_info"],
)

RESULT_TEMPLATE = """
당신은 검색 결과 출력을 담당하는 전문가입니다.
사용자 질문과 단계별 도구 실행 결과 목록이 주어집니다.
각 단계는 plan 리스트 내의 JSON 객체로 표현됩니다.
각 객체의 중요 필드는 다음과 같습니다.
- tool: 호출된 도구의 이름
- args: 도구 호출시 사용한 질의와 해당 도구의 선택 이유
- tool_result: 도구 실행 결과
- evaluation: 도구 실행 결과에 대한 평가

지침:
- 도구 실행 결과를 종합하여 질문 의도와 직접적으로 관련되지 않은 결과는 제거하세요.
- 동일한 정보가 반복된다면 가장 대표적인 항목만 남기세요.
- 질문에 답하기 위해 필요한 최소 개수의 결과만 선택하세요.
- 선택된 결과를 종합하여 상품들에 대한 설명을 요약 및 작성하여 'results' 리스트에 포함하세요. 이 때, 사용자에게 꼭 필요한 것으로 판단되는 정보만을 포함하세요. 상품명과 월정액은 반드시 포함해야합니다.
- 그리고 선택된 상품들의 '고유ID' 필드만 추출하여 'unique_ids' 리스트에 포함하세요.

아래 JSON 형식을 정확히 따라 응답하세요:
{{
    "unique_ids": [<선택된 결과의 고유ID 값 (문자열)>, ...],
    "results": [<선택된 상품에 대한 요약>, ...],
    "comment": ["<선택 이유에 대한 간단한 설명 (한글)>", ...]
}}

추가 텍스트를 포함하지 마세요.

사용자 질문: {user_query}
검색 결과: {plans}
"""

RESULT_PROMPT = PromptTemplate(
    template=RESULT_TEMPLATE,
    input_variables=["user_query", "plans"],
)

EVALUATION_TEMPLATE = """
당신은 검색 에이전트가 호출한 도구의 실행 결과를 검증하는 평가자입니다.
아래 정보를 정독한 뒤, 도구 선택 이유(tool_select_reason)가 실제 결과와 부합하는지 확인하고,
재계획 여부를 결정하세요.

반드시 JSON 객체만 출력하며, 형식은 다음을 따릅니다:
{{
  "accepted": bool,             # 도구 실행이 만족스러운지 여부
  "score": float,               # 0.0~1.0 사이의 점수
  "detail": {{
    "reason": string,           # 평가 요약 코드(ex: "success", "reason_not_met")
    "message": string,          # 평가 설명 및 판단 근거 (한글)
  }}
}}

평가 시 지켜야 할 규칙:
- tool_select_reason이 주어진 경우, 결과 데이터에 해당 목적이 충족되었는지 엄격히 확인합니다.
- 가장 비싼, 가장 싼 등의 최상급 비교 문구가 질문에 포함된 경우, 결과가 하나만 있어도 됩니다.
- 질문에 지정된 갯수만큼의 결과를 얻지 못했더라도 질문에 부합하는 결과가 있다면 성공으로 간주합니다.
- 결과가 비어 있거나 오류가 포함되어 있으면 실패로 간주합니다.
- 추가적인 텍스트나 설명은 출력하지 말고 JSON만 반환합니다.

원본 질문:
{original_question}

재시도 정보: 현재 {retry_count}회 / 최대 {max_retries}회

도구 실행 로그(JSON):
{steps_json}
"""

EVALUATION_PROMPT = PromptTemplate(
    template=EVALUATION_TEMPLATE,
    input_variables=["original_question", "retry_count", "max_retries", "steps_json"],
)

REPLAN_FAILURE_TEMPLATE = """
당신은 검색 에이전트의 오퍼레이터입니다.
직전 단계의 도구 실행이 실패했습니다. 
아래 정보를 참고하여 같은 질문을 해결하기 위해 어떤 도구를 어떤 인자로 호출할지 결정하세요.
동일한 도구를 사용하더라도 도구 호출 파라미터를 변경하면 올바른 결과를 얻을 가능성이 있습니다.
동일한 도구를 호출할 경우 실패한 단계와 동일한 질문을 사용하지 말고 실패한 이유를 분석해서 새로운 질문을 만드세요.

OpenAI 함수 호출 스펙이 tools 파라미터로 주어집니다. 
해당 도구 중 하나를 선택하여 함수 호출 형태의 JSON으로 응답하세요. 
사용자ID(user_id 또는 svcMgmtNum)가 필요한 도구에는 반드시 user_id 값을 그대로 사용하세요.
user_id: {user_id}

### 참고 정보
- 원본 질문: {original_question}
- 실패한 단계의 도구 호출 인자: {last_args}
- 실패한 단계의 도구 호출 결과: {tool_result}
- 실패 이유: {last_evaluation}
"""

REPLAN_FAILURE_PROMPT = PromptTemplate(
    template=REPLAN_FAILURE_TEMPLATE,
    input_variables=[
        "original_question",
        "last_args",
        "tool_result",
        "last_evaluation",
        "user_id",
    ],
)

REPLAN_SUCCESS_TEMPLATE = """
당신은 검색 에이전트의 오퍼레이터입니다.
직전 도구 실행은 성공했습니다. 이제 남은 질문을 해결하기 위해 추가 도구 호출이 필요한지 판단하세요.

OpenAI 함수 호출 스펙이 tools 파라미터로 주어집니다. 
추가 실행이 필요하다면 해당 도구 중 하나를 선택해 함수 호출 형태의 JSON으로 응답하세요.
사용자ID(user_id 또는 svcMgmtNum)가 필요한 도구에는 반드시 user_id 값을 그대로 사용하세요.
user_id: {user_id}

더 이상 실행이 필요 없다면 도구를 호출하지 말고 이유를 {{"comment": "..."}} 형태로 반환하세요.

### 참고 정보
- 원본 질문: {original_question}
- 현재까지의 실행 결과: {all_plans}
"""

REPLAN_SUCCESS_PROMPT = PromptTemplate(
    template=REPLAN_SUCCESS_TEMPLATE,
    input_variables=[
        "original_question",
        "all_plans",
        "user_id",
    ],
)

SUMMARY_PROMPT = PromptTemplate(
    template=SUMMARY_TEMPLATE,
    input_variables=["user_query", "search_results", "execution_stats"],
)

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question", "fewshot_examples"],
    template=CYPHER_GENERATION_TEMPLATE,
)
