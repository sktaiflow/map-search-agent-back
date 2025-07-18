
import json
import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from src.app.agents.utils import call_smartbee
from src.app.tools import get_service_info, get_subscribed_products, prod_meta_search

logging.basicConfig(level=logging.INFO)

tools = [get_service_info, prod_meta_search]

PLANNING_SYS_PROMPT = f"""You are responsible for the Plan stage of LangGraph. 
    Given inputs userQuery and userId, return an array of execution steps combining the available tools.

    Available tools:
    {json.dumps([{"name": t.name} for t in tools], indent=2, ensure_ascii=False)}

    Follow this format strictly:
    {{"plan": [{{"step": 1, "tool": "tool_name", "reason": "reason for use"}}, ...]}}
"""

def plan_step(state: Dict[str, Any]) -> Dict[str, Any]:
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
    return state

def execute_step(state: Dict[str, Any]) -> Dict[str, Any]:
    plan = state["plan"]
    task = plan[0]["reason"]

    system_message = f"""You are an AI assistant that selects the best function for a given task.
        Respond ONLY with a tool_call in valid JSON format like below:
        {{
        "tool_calls": [
            {{
            "function": {{
                "name": "prod_meta_search",
                "arguments": "{{\\"query\\": \\"무제한 요금제\\"}}"
            }}
            }}
        ]
        }}

        User query: {state["input"]}
        Plan: {plan}
        Previous results: {state.get("past_steps", "None")}
        Current task: {task}
    """

    logging.info(f"[execute_step]{system_message}")
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
    # logging.info(f"[tool_calls]{tool_calls}")
    if tool_calls:
        tool = tool_calls[0]["function"]["name"]
        args = json.loads(tool_calls[0]["function"]["arguments"])
        result = None
        result_metadata = {}

        if tool == "prod_meta_search":
            result_dict = prod_meta_search(args["query"])
            result = result_dict.get("result")
            result_metadata = result_dict.get("result_metadata", {})
            state["product_meta"] = result
        elif tool == "get_service_info":
            state["user_info"] = get_service_info(args["svc_mgmt_num"])
        elif tool == "get_subscribed_products":
            state["user_info"] = get_subscribed_products(args["svc_mgmt_num"])

        state["past_steps"].append({
            "task": task,
            "tool": tool,
            "query": args,
            "result": result,
            "result_metadata": result_metadata
        })
    return state

def replan_step(state: Dict[str, Any]) -> Dict[str, Any]:
    # 1. 실패한 step 모으기
    failed_steps = []
    for step in state.get("past_steps", []):
        metadata = step.get("result_metadata", {})
        if not metadata.get("validated", False):
            failed_steps.append({
                "task": step.get("task"),
                "tool": step.get("tool"),
                "llm_feedback": metadata.get("llm_response", "N/A"),
                "notes": metadata.get("notes", "")
            })

    # 2. System prompt 구성
    system_message = f"""
        당신은 LangGraph의 검증자 역할입니다.

        - 아래의 tool 실행 결과 중 문제가 있는 항목이 있다면 plan을 다시 작성해야 합니다.
        - 문제가 없다면 최종 응답을 작성하세요.

        Input: {state["input"]}
        Plan: {json.dumps(state["plan"], ensure_ascii=False, indent=2)}
        Results: {json.dumps(state["past_steps"], ensure_ascii=False, indent=2)}
        Errors: {json.dumps(failed_steps, ensure_ascii=False, indent=2)}
    """

    # 3. LLM 호출
    response = call_smartbee(
        messages=[],
        system_message=system_message,
        tools=[],
        response_format={"type": "json_object"},
        expect_json=True,
    )

    # 4. 결과 해석
    try:
        parsed = json.loads(response.content)
        if "plan" in parsed:
            state["plan"] = parsed["plan"]
        elif "response" in parsed:
            state["response"] = parsed["response"]
    except Exception:
        state["response"] = response.content

    return state

def should_end(state: Dict[str, Any]) -> str:
    return END if state.get("response") else "agent"

workflow = StateGraph(dict)
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_step)
workflow.add_node("replan", replan_step)
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "replan")
workflow.add_conditional_edges("replan", should_end)
app = workflow.compile()
