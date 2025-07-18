import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph, parallel

from src.app.agents.schema.schema import AgentState
from src.app.agents.utils import call_smartbee, resolve_tool

logging.basicConfig(level=logging.INFO)

tools = [get_service_info, prod_meta_search]

PLANNING_SYS_PROMPT = f"""당신은 LangGraph 시스템에서 '계획 수립'을 담당하는 AI입니다.
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

def plan_step(state: AgentState) -> AgentState:
    response = call_smartbee(
        messages=[HumanMessage(content=state["input"])],
        system_message=PLANNING_SYS_PROMPT,
        tools=[],
        response_format={"type": "json_object"},
        expect_json=True,
    )
    try:
        state["plan"] = response["plan"]
    except Exception:
        state["plan"] = [response.content]
    state["past_steps"] = []
    state["step_index"] = 0
    return state

# ✅ 실행할 각 step 하나를 처리하는 함수 (단일 step 단위로 수행)
def execute_single_step(data: tuple) -> tuple:
    state, step = data
    tool = step["tool"]
    task = step["reason"]
    args = step.get("args", {})

    logging.info(f"[agent-parallel] executing step: {tool} ({task})")
    try:
        result = resolve_tool(tool, args)
        state["past_steps"].append({
            "task": task,
            "tool": tool,
            "query": args,
            "result": result.get("result") if isinstance(result, dict) else result,
            "result_metadata": result.get("result_metadata", {})
        })
        if tool == "prod_meta_search":
            state["product_meta"] = result.get("result")
        elif tool in {"get_service_info", "get_subscribed_products"}:
            state["user_info"] = result

    except Exception as e:
        state["past_steps"].append({
            "task": task,
            "tool": tool,
            "query": args,
            "result": None,
            "result_metadata": {"validated": False, "exception": True, "error": str(e)}
        })

    return state, step

# ✅ 병렬 실행을 위한 실행 함수

def execute_steps(state: AgentState) -> AgentState:
    steps = state.get("plan", [])
    data = [(state, step) for step in steps]
    results = parallel(execute_single_step)(data)
    return results[0][0]  # 병합된 state 반환

def store_result(state: AgentState, tool: str, result: dict, task: str, args: dict) -> None:
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

def execute_step(state: AgentState) -> AgentState:
    plan = state["plan"]
    step_index = state.get("step_index", 0)
    if step_index >= len(plan):
        state["response"] = "🤖 계획을 모두 수행했습니다."
        return state

    current_step = plan[step_index]
    task = current_step["reason"]
    tool = current_step["tool"]

    # 툴 선택용 system_message 구성
    system_message = f"""당신은 사용자의 요청에 가장 적합한 도구를 선택해야 하는 AI 도우미입니다.
        아래 예시와 같은 JSON 형식의 응답만 반환해야 합니다 (그 외 텍스트는 포함하지 마세요):
        {{
        "tool_calls": [
        {{
            "function": {{
            "name": "prod_meta_search",
            "arguments": "{{\\\\"query\\\\": \\\\"무제한 요금제\\\\"}}"
            }}
        }}
        ]
        }}

        사용자 질문: {state["input"]}
        수행할 전체 계획: {plan}
        이전 단계 결과: {state.get("past_steps", "없음")}
        현재 작업 설명: {task}
    """

    logging.info(f"[execute_step] {system_message}")

    # 캐시 검사: 동일 tool + 동일 args
    for step in state["past_steps"]:
        if step["tool"] == tool and step["query"] == current_step.get("args", {}):
            logging.info("✅ 이전 결과 재사용")
            store_result(state, tool, step, task, current_step.get("args", {}))
            state["step_index"] += 1
            return state

    # 툴 선택 LLM 호출
    try:
        response = call_smartbee(
            messages=[],
            system_message=system_message,
            tools=tools,
            expect_json=True,
        )
    except Exception as e:
        logging.exception("🔥 call_smartbee 실패")
        raise

    tool_calls = response.get("tool_calls", [])
    if tool_calls:
        tool = tool_calls[0]["function"]["name"]
        args = json.loads(tool_calls[0]["function"]["arguments"])

        # 툴 실행 + 결과 저장
        result = resolve_tool(tool, args)
        store_result(state, tool, result, task, args)

    state["step_index"] = step_index + 1
    return state

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


def create_final_response(state: AgentState, failed_steps: list) -> AgentState:
    system_message = f"""
        당신은 LangGraph의 검증자이며, 모든 tool 실행 결과를 바탕으로 최종 응답을 생성해야 합니다.

        요구되는 출력 형식은 다음과 같습니다:
        {{
        "response": "최종 자연어 응답 (사용자에게 보여질 형태)",
        "reasoning": "이 응답을 도출한 이유나 추론 근거",
        "raw_results": {{
            "product_meta": ...,
            "user_info": ...
        }}
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

    response = call_smartbee(
        messages=[],
        system_message=system_message,
        tools=[],
        response_format={"type": "json_object"},
        expect_json=True,
    )

    try:
        parsed = json.loads(response.content)
        state["response"] = parsed.get("response", "응답이 생성되지 않았습니다.")
        state["reasoning"] = parsed.get("reasoning", "추론 정보 없음")
        state["raw_results"] = {
            "product_meta": state.get("product_meta"),
            "user_info": state.get("user_info")
        }
    except Exception:
        state["response"] = response.content
        state["reasoning"] = "LLM JSON 파싱 실패로 기본 응답을 제공합니다."
        state["raw_results"] = {
            "product_meta": state.get("product_meta"),
            "user_info": state.get("user_info")
        }

    return state


def replan_step(state: AgentState) -> AgentState:
    failed_steps = validate_steps(state)
    return create_final_response(state, failed_steps)

def should_end(state: AgentState) -> str:
    return END if state.get("response") else "agent"

workflow = StateGraph(AgentState)
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_steps)
workflow.add_node("replan", replan_step)
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "replan")
workflow.add_conditional_edges("replan", should_end)
app = workflow.compile()