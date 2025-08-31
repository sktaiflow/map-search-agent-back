from string import Template
from langchain_core.prompts.prompt import PromptTemplate

PLANNING_TEMPLATE = """
    당신은 LangGraph 시스템에서 '계획 수립'을 담당하는 AI입니다.
    아래의 사용자 질문을 바탕으로, 순차적 또는 병렬 실행이 필요한 작업 목록을 JSON 형식으로 작성하세요. 
    
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

# PromptTemplate 객체로 생성
PLANNING_PROMPT = PromptTemplate(
    template=PLANNING_TEMPLATE, input_variables=["format_instructions", "tool_list_json"]
)

# LLM 기반 콘텐츠 생성용 프롬프트 템플릿들
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
    input_variables=["user_query", "search_results", "execution_summary"]
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

SUMMARY_PROMPT = PromptTemplate(
    template=SUMMARY_TEMPLATE,
    input_variables=["user_query", "search_results", "execution_stats"]
)

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

REASONING_PROMPT = PromptTemplate(
    template=REASONING_TEMPLATE,
    input_variables=["user_query", "search_case", "execution_steps", "retry_info"]
)
