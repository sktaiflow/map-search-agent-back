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
        state["product_meta"] = result.get("result")
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
    
    system_message = f"""
    당신은 LangGraph의 검증자이며, 모든 tool 실행 결과를 바탕으로 최종 응답을 생성해야 합니다.

    요구되는 출력 형식은 다음과 같은 JSON 형식입니다:
    {{
      "response": "최종 자연어 응답 (사용자에게 보여질 형태)",
      "reasoning": "이 응답을 도출한 이유나 추론 근거"
    }}

    다음은 context입니다:

    질문: {state["input"]}

    계획:
    {json.dumps(state["plan"], ensure_ascii=False, indent=2)}

    수행된 단계 및 결과:
    {json.dumps(state["past_steps"], ensure_ascii=False, indent=2)}

    실패한 단계:
    {json.dumps(failed_steps, ensure_ascii=False, indent=2)}
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
            final_response = response_dict.get("response", "응답이 생성되지 않았습니다.")
            reasoning = response_dict.get("reasoning", "추론 정보 없음")
            
            state["response"] = final_response
            state["reasoning"] = reasoning
            
            logger.info(f"✅ 최종 응답 설정 완료: {final_response[:100]}...")
        else:
            logger.error(f"❌ LLM 응답이 dict가 아님: {type(response_dict)}")
            state["response"] = "최종 응답을 생성하는 데 실패했습니다."
            state["reasoning"] = f"파싱 실패. LLM 응답: {response_dict}"

        # raw_results 설정
        state["raw_results"] = {
            "product_meta": state.get("product_meta"),
            "user_info": state.get("user_info")
        }
        
        logger.info(f"🎯 create_final_response 함수 완료. state 최종 키들: {list(state.keys())}")
        return state

    except Exception as e:
        logger.exception("🔥 create_final_response 함수에서 예외 발생")
        state["response"] = f"최종 응답 생성 중 오류가 발생했습니다: {str(e)}"
        state["reasoning"] = "예외 발생으로 인한 오류"
        return state