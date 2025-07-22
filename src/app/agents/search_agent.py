# src/app/agents/search_agent.py

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from src.app.agents.call_helpers import (
    complete_args,
    create_final_response,
    store_result,
    validate_steps,
)
from src.app.agents.llm_caller import call_smartbee
from src.app.agents.prompts import PLANNING_SYS_PROMPT
from src.app.agents.schema.schema import AgentState
from src.app.tools.tool_registry import resolve_tool, tool_registry

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- 노드 함수 정의: 그래프의 각 단계를 구성 ---

def plan_step(state: AgentState) -> AgentState:
    """
    사용자의 입력을 바탕으로 작업 계획(plan)을 수립합니다.
    LLM을 호출하여 도구 사용 순서와 방법을 결정합니다.
    """
    logger.info("--- 🧠 계획 수립 단계 시작 ---")
    
    # 도구 목록을 JSON 형식으로 준비
    tool_list_json = json.dumps(
        [{"name": name} for name in tool_registry.keys()],
        indent=2,
        ensure_ascii=False
    )
    
    # 프롬프트 포맷팅
    formatted_prompt = PLANNING_SYS_PROMPT.format(tool_list_json=tool_list_json)

    response = call_smartbee(
        messages=[HumanMessage(content=state["input"])],
        system_message=formatted_prompt,
        response_format={"type": "json_object"},
        expect_json=True,
    )
    
    plan = response.get("plan", [])
    logger.info(f"수립된 계획: {plan}")
    
    state["plan"] = plan
    state["past_steps"] = []  # 계획을 새로 수립할 때마다 과거 기록은 초기화
    return state


def execute_single_step(state: AgentState, step: dict) -> None:
    """
    계획에 명시된 단일 작업을 실행합니다.
    인자가 부족할 경우 LLM을 통해 보완을 시도합니다.
    """
    tool = step["tool"]
    task = step["reason"]
    args = step.get("args")

    logger.info(f"  - 🔨 단일 작업 실행 시작: {tool} (이유: {task})")

    if not args or not isinstance(args, dict):
        logger.warning(f"    - 인자 누락! LLM으로 보완 시도: {tool}")
        args = complete_args(tool, args, state)
        if args is None:
            logger.error(f"    - 인자 보완 실패. {tool} 실행 중단.")
            # 실패 기록을 남기는 로직을 추가할 수 있습니다.
            return

    try:
        result = resolve_tool(tool, args)
        store_result(state, tool, result, task, args)
    except Exception as e:
        logger.exception(f"  - 🔥 '{tool}' 실행 중 심각한 에러 발생!")
        # 에러 발생 시에도 past_steps에 실패 기록을 남깁니다.
        state["past_steps"].append({
            "task": task,
            "tool": tool,
            "query": args,
            "result": None,
            "result_metadata": {
                "validated": False,
                "exception": True,
                "error": str(e)
            }
        })


def execute_steps(state: AgentState) -> AgentState:
    """
    수립된 계획(plan)에 따라 병렬 또는 순차적으로 작업을 실행합니다.
    """
    logger.info("--- 🚀 작업 실행 단계 시작 ---")
    plan = state.get("plan", [])
    if not plan:
        logger.warning("실행할 계획이 없습니다.")
        return state

    # ✨ [리팩토링] 병렬/순차 실행 로직 명확화
    # 계획의 모든 단계가 'parallel' 모드일 때만 병렬 실행
    if all(step.get("mode") == "parallel" for step in plan):
        logger.info("모든 작업을 병렬로 실행합니다.")
        with ThreadPoolExecutor(max_workers=len(plan)) as executor:
            # 각 스레드에 state의 복사본을 전달하여 동시성 문제를 방지할 수 있으나,
            # 현재 store_result가 리스트에 append만 하므로 일단 그대로 둡니다.
            futures = [executor.submit(execute_single_step, state, step) for step in plan]
            for future in as_completed(futures):
                future.result()  # 작업 중 발생한 예외를 확인하기 위해 .result() 호출
    else:
        logger.info("작업을 순차적으로 실행합니다.")
        for step in plan:
            execute_single_step(state, step)
            
    logger.info("--- ✅ 작업 실행 단계 완료 ---")
    return state


def replan_or_finish(state: AgentState) -> str:
    """
    실행 결과를 검증하고, 다음 단계를 결정합니다.
    """
    logger.info("--- 🤔 재계획 또는 종료 결정 단계 시작 ---")
    failed_steps = validate_steps(state)
    
    if not failed_steps:
        logger.info("모든 작업 성공. 최종 응답 생성으로 이동.")
        return "final_response"  # 최종 응답 생성 노드로 이동
    else:
        logger.warning(f"실패한 작업이 있습니다: {failed_steps}")
        logger.info("재계획이 필요합니다. 계획 단계로 돌아갑니다.")
        return "planner"  # 재계획


def create_final_response_node(state: AgentState) -> AgentState:
    """
    최종 응답을 생성하는 노드 함수입니다.
    """
    logger.info("--- 🎯 최종 응답 생성 노드 시작 ---")
    
    failed_steps = validate_steps(state)
    updated_state = create_final_response(state, failed_steps)
    state.update(updated_state)
    
    logger.info(f"✅ 최종 응답 생성 완료. state 키들: {list(state.keys())}")
    return state


# --- LangGraph 워크플로우 정의 ---

workflow = StateGraph(AgentState)

# 1. 노드 추가: 그래프의 각 상태(작업 단위)를 정의
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_steps)
workflow.add_node("final_response", create_final_response_node)  # ✅ 새 노드 추가

# 2. 엣지(연결선) 추가: 상태 간의 흐름을 정의
workflow.set_entry_point("planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("final_response", END)  # ✅ 최종 응답 노드에서 종료

# 3. 조건부 엣지 추가: 특정 조건에 따라 다음 상태를 결정
workflow.add_conditional_edges(
    "agent",
    replan_or_finish,  # 이 함수가 "final_response" 또는 "planner"를 반환
    {
        "final_response": "final_response",  # ✅ 최종 응답 노드로 이동
        "planner": "planner"  # 재계획으로 이동
    }
)

# 4. 그래프 컴파일
app = workflow.compile()

logger.info("LangGraph 워크플로우가 성공적으로 컴파일되었습니다.")