
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
    logging.info(f"[tool_calls]{tool_calls}")
    if tool_calls:
        tool = tool_calls[0]["function"]["name"]
        args = json.loads(tool_calls[0]["function"]["arguments"])
        if tool == "prod_meta_search":
            _, result = prod_meta_search(args["query"])
            state["product_meta"] = result
        elif tool == "get_service_info":
            state["user_info"] = get_service_info(args["svc_mgmt_num"])
        elif tool == "get_subscribed_products":
            state["user_info"] = get_subscribed_products(args["svc_mgmt_num"])
        state["past_steps"].append((task, str(result)))
    return state

def replan_step(state: Dict[str, Any]) -> Dict[str, Any]:
    system_message = f"""You are responsible for the Re-plan stage of LangGraph.
        Query: {state["input"]}
        Plan: {state["plan"]}
        Results: {state["past_steps"]}
        Return updated plan or final response.
        If replan needed -> {{"plan": [...]}}, else -> {{"response": "..."}}
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
