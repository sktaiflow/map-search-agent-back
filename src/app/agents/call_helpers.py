# ✅ call_helpers.py (최종 완성본)

import json
import logging

from langchain.schema import SystemMessage

from src.app.agents.llm_caller import call_smartbee
from src.app.agents.schema.schema import AgentState
from src.app.tools.tool_registry import tool_registry

logger = logging.getLogger(__name__)


# ✅ planner 내 LLM 호출 분리
def plan_with_llm(user_input: str, tools: list) -> dict:
    system_message = f"""당신은 LangGraph 시스템에서 '계획 수립'을 담당하는 AI입니다.
    아래의 사용자 질문과 사용자 ID를 참고하여, 주어진 도구 목록을 활용해
    순차적으로 실행할 작업 목록(plan)을 JSON 형식으로 생성하세요.

    도구 목록:
    {json.dumps([{"name": t.name} for t in tools], indent=2, ensure_ascii=False)}

    다음과 같은 형식을 반드시 따르세요:
    {{
      "plan": [
        {{"step": 1, "tool": "tool_name", "reason": "사용 이유"}},
        ...
      ]
    }}
    """
    from src.app.agents.utils import call_smartbee
    return call_smartbee(
        messages=[SystemMessage(content=system_message), SystemMessage(content=user_input)],
        system_message=None,
        tools=[],
        response_format={"type": "json_object"},
        expect_json=True
    )


# ✅ args가 누락된 경우 보완

def complete_args(tool: str, args: dict, state: AgentState) -> dict:
    # 이 함수는 이미 args가 없거나 비어있을 때만 호출되므로,
    # 첫 번째 if문은 search_agent.py의 로직과 중복되어 제거해도 됩니다.

    logger.info(f"🧠 args 누락 → LLM으로 보완 시도: {tool}")

    # ✅ 1. 도구의 스키마(필요한 인자 정보)를 가져옵니다.
    # tool_registry에서 실제 도구 함수를 찾습니다.
    tool_func = tool_registry.get(tool, {}).get("func")
    if not tool_func or not hasattr(tool_func, 'args_schema'):
        logger.error(f"'{tool}' 도구나 args_schema를 찾을 수 없습니다.")
        return {}

    # Pydantic 모델로부터 필요한 인자 스키마를 JSON 형태로 가져옵니다.
    schema_json = json.dumps(tool_func.args_schema.schema(), ensure_ascii=False, indent=2)

    # ✅ 2. OpenAI JSON 모드 요구사항에 맞게 프롬프트를 수정합니다.
    system_message = f"""
    당신은 주어진 도구를 실행하기 위해 누락된 인자를 생성하는 AI입니다.
    사용자의 이전 대화 내용과 도구가 요구하는 JSON 스키마를 바탕으로,
    필요한 인자 값을 채워서 완벽한 JSON 객체를 생성해야 합니다.

    사용자 질문: {state['input']}
    이전 대화 및 실행 기록: {json.dumps(state['past_steps'], ensure_ascii=False, indent=2)}
    
    실행할 도구: '{tool}'
    
    이 도구가 요구하는 인자의 JSON 스키마는 다음과 같습니다:
    {schema_json}

    위 정보를 바탕으로, 도구 실행에 필요한 인자를 JSON 형식으로만 응답하세요.
    """
    
    try:
        # ✅ 3. call_smartbee가 이미 dict를 반환하므로, json.loads는 필요 없습니다.
        response_dict = call_smartbee(
            messages=[],
            system_message=system_message,
            tools=[],
            response_format={"type": "json_object"},
            expect_json=True,
        )
        
        logger.info(f"LLM이 생성한 보완된 인자: {response_dict}")
        
        # LLM이 생성한 값이 딕셔너리인지 확인 후 반환
        return response_dict if isinstance(response_dict, dict) else {}

    except Exception as e:
        logger.exception("🔥 arguments 보완 실패")
        return {}


# ✅ 툴 실행 결과 저장

def store_result(state: AgentState, tool: str, result: dict, task: str, args: dict):
    if tool == "prod_meta_search":
        state["product_meta"] = result.get("raw_data", [])
    elif tool in {"get_service_info", "get_subscribed_products"}:
        state["user_info"] = result

    state["past_steps"].append({
        "task": task,
        "tool": tool,
        "query": args,
        "result": result.get("result") if isinstance(result, dict) else result,
        "result_metadata": result.get("result_metadata", {})
    })


# ✅ 실패 step 검증

def validate_steps(state: AgentState) -> list:
    failed = []
    for step in state.get("past_steps", []):
        metadata = step.get("result_metadata", {})
        if not metadata.get("validated", True):
            failed.append({
                "task": step.get("task"),
                "tool": step.get("tool"),
                "llm_feedback": metadata.get("llm_response", "N/A"),
                "notes": metadata.get("notes", ""),
                "metadata": metadata
            })
    return failed


# ✅ 최종 응답 생성
def create_final_response(state: AgentState, failed_steps: list) -> AgentState:
    logger.info("🎯 create_final_response 함수 시작")
    logger.info(f"입력된 state 키들: {list(state.keys())}")
    logger.info(f"failed_steps: {failed_steps}")
    
    # 실제 검색된 데이터 추출
    product_data = state.get("product_meta", [])
    
    system_message = f"""
    당신은 SKT 요금제 전문 상담원입니다. 검색된 실제 데이터를 바탕으로 고객에게 실질적으로 도움이 되는 3단계 응답을 JSON 형식으로 생성하세요.

    요구되는 JSON 출력 형식:
    {{
      "response": {{
        "raw_data": [실제 검색된 상품들의 핵심 정보를 구조화],
        "summary": "가격대별, 혜택별로 분류한 구체적 요약",
        "insights": "실제 추천과 주의사항, 비교분석"
      }},
      "reasoning": "분석 근거"
    }}

    사용자 질문: {state["input"]}

    검색된 실제 데이터:
    {json.dumps(product_data, ensure_ascii=False, indent=2)}

    JSON 응답 작성 가이드라인:
    
    1. raw_data 작성 시:
    - 상품명, 월정액, 주요혜택, 가입조건을 필수 포함
    - 원본 데이터의 구체적 수치와 조건을 그대로 활용
    - 단순히 "무제한 데이터" 같은 일반론 금지
    
    2. summary 작성 시:
    - 가격대별로 분류 (6만원대, 7만원대, 9만원대, 10만원대 등)
    - 연령제한 있는 요금제와 일반 요금제 구분
    - 온라인 전용 vs 일반 가입채널 구분
    - 구체적인 혜택별 분류 (디즈니+, 유튜브, 스마트기기 등)
    
    3. insights 작성 시:
    - 실제 가격 비교와 가성비 분석
    - 연령, 사용패턴에 따른 구체적 추천
    - 약정할인 적용 시 실제 절약 금액
    - 각 혜택의 실제 가치 분석 (예: 디즈니+ 월 구독료 9,900원)
    - 주의사항: 가입조건, 연령제한, 온라인 전용 등
    
    절대 금지사항:
    - "다양한 혜택을 제공합니다" 같은 뻔한 표현
    - "고려해보세요" 같은 추상적 조언
    - 구체적 수치 없는 일반론
    
    반드시 유효한 JSON 형식으로만 응답하세요.
    """
    
    try:
        logger.info("🤖 LLM 호출 시작")
        # ✅ --- 중복 제거: call_smartbee를 한 번만 호출합니다 --- ✅
        response_dict = call_smartbee(
            messages=[],
            system_message=system_message,
            tools=[],
            response_format={"type": "json_object"},
            expect_json=True, 
        )
        
        logger.info(f"🤖 LLM 응답 받음: {response_dict}")
        logger.info(f"응답 타입: {type(response_dict)}")

        # 응답 처리
        if isinstance(response_dict, dict):
            response_data = response_dict.get("response", {})
            reasoning = response_dict.get("reasoning", "추론 정보 없음")
            
            # 3단계 구조로 response 설정
            if isinstance(response_data, dict):
                state["response"] = {
                    "raw_data": response_data.get("raw_data", state.get("product_meta", [])),
                    "summary": response_data.get("summary", "요약 정보가 생성되지 않았습니다."),
                    "insights": response_data.get("insights", "인사이트가 생성되지 않았습니다.")
                }
            else:
                # 레거시 호환: 기존 문자열 응답을 insights로 처리
                state["response"] = {
                    "raw_data": state.get("product_meta", []),
                    "summary": "검색 결과를 요약하지 못했습니다.",
                    "insights": response_data if isinstance(response_data, str) else "응답이 생성되지 않았습니다."
                }
            
            state["reasoning"] = reasoning
            
            logger.info(f"✅ 3단계 응답 설정 완료")
            logger.info(f"  - raw_data: {len(state['response']['raw_data']) if isinstance(state['response']['raw_data'], list) else 'N/A'} items")
            logger.info(f"  - summary: {state['response']['summary'][:50]}...")
            logger.info(f"  - insights: {state['response']['insights'][:50]}...")
        else:
            logger.error(f"❌ LLM 응답이 dict가 아님: {type(response_dict)}")
            state["response"] = {
                "raw_data": state.get("product_meta", []),
                "summary": "응답 생성에 실패했습니다.",
                "insights": f"파싱 실패. LLM 응답: {response_dict}"
            }
            state["reasoning"] = "응답 파싱 실패"

        # raw_results 설정
        state["raw_results"] = {
            "product_meta": state.get("product_meta"),
            "user_info": state.get("user_info")
        }
        
        logger.info(f"🎯 create_final_response 함수 완료. state 최종 키들: {list(state.keys())}")
        return state

    except Exception as e:
        logger.exception("🔥 create_final_response 함수에서 예외 발생")
        state["response"] = {
            "raw_data": state.get("product_meta", []),
            "summary": f"응답 생성 중 오류가 발생했습니다: {str(e)}",
            "insights": "예외로 인해 인사이트를 생성할 수 없습니다."
        }
        state["reasoning"] = "예외 발생으로 인한 오류"
        return state