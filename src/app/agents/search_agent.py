import asyncio
import operator
import json

from typing import Annotated, List, Tuple, Optional, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    FunctionMessage,
)
from langchain_core.callbacks import StreamingStdOutCallbackHandler

from src.app.tools import get_service_info, get_subscribed_products, prod_meta_search, thinking_tool
from src.app.agents.utils import tool_to_openai_function, call_pe_tool_v2, call_ollama
from src.app.agents.utils import neo4j_connect
from src.app.agents.schema import PlanExecuteState, Plan, Response

import logging
from src.app.agents.logging_config import setup_logging

logger = logging.getLogger(__name__)

# tools = [get_service_info, get_subscribed_products, prod_meta_search]
tools = [get_service_info, prod_meta_search]
openai_tools = [tool_to_openai_function(t) for t in tools]
openai_tools_json = json.dumps(openai_tools, ensure_ascii=False, indent=2)
user_search_tools = [get_service_info, get_subscribed_products]
user_search_tools_json = [tool_to_openai_function(t) for t in user_search_tools]

# graph = neo4j_connect(env="openwebui", enhanced_schema=True)

PLANNING_SYS_PROMPT = f"""You are responsible for the Plan stage of LangGraph. 
Given inputs userQuery and userId, return an array of execution steps combining the available tools.
Each element in the output array must include:

- step: execution order number
- tool: name of the tool to call
- reason: the reason why this tool is needed for the current step

Available tools:
{openai_tools_json}

Additional rules:
- '이상' means 'greater than or equal to', and '이하' means 'less than or equal to'. 
- '초과' means 'greater than', and '미만' means 'less than'.
- If there is a number in the query and there are not '이상', '이하', '초과', or '미만' in the query, you can assume that the user is looking for an exact match.
- '무제한' means 'unlimited', and it should be replaced with 99999.
- Use get_service_info tool only if the query contains the first person pronoun and the user's information is needed generate the cypher.
- Determine whether to send the query directly to prod_meta_search or add additional information to the original query, and decide the order of the steps and the tools to be used. 
For example, if the user query requires comparison with the user's current plan, you should first use get_service_info to retrieve the name of user's current plan, and then use prod_meta_search to find it and other plans to be compared.

Examples
- {{"svc_mgmt_num": "12345", "userQuery": "무제한 요금제 알려줘"}} -> {{"plan": [{{"step": 1, "tool": "prod_meta_search", "reason": "To find the unlimited plan"}}]}}
- {{"svc_mgmt_num": "12345", "userQuery": "내가 가입할 수 있는 넷플릭스 할인되는 10만원 이하 요금제 알려줘"}} -> {{"plan": [{{"step": 1, "tool": "get_service_info", "reason": "To get the basic information of the user"}}, {{"step": 2, "tool": "prod_meta_search", "reason": "To fine the Netflix discount plan under the 100000 won and available for the user. It requries basic information from previous steps"}}]}}
- {{"svc_mgmt_num": "12345", "userQuery": "지금 요금제보다 싸고 데이터 무제한인 요금제 알려줘"}} -> {{"plan": [{{"step": 1, "tool": "get_service_info", "reason"; "To get the monthly price of the user's current plan"}}, {{"step": 2, "tool": "prod_meta_search", "reason": "To find the unlimited plan cheaper than the user's current plan. Information about user's current plan could be gotten from this step"}}]}}
- {{"svc_mgmt_num": "12345", "userQuery": "24세가 가입할 수 있는 웨이브 할인되는 가장 싼 요금제 알려줘"}} -> {{"plan": [{{"step": 1, "tool": "prod_meta_search", "reason": "To find the cheapest plan with Wavve discount for the 24 years old"}}]}}

Adhere strictly to this format and output only the JSON array without any additional styling or emphasis.
"""


# class PlanExecuteState(TypedDict):
#     input: str
#     plan: List[str]
#     past_steps: Optional[List[Tuple]]
#     response: Optional[str]
#     user_info: Optional[Dict[str, Any]]
#     product_meta: Optional[Dict[str, Any]]
#     messages: Annotated[list, add_messages]
#     cypher: Optional[str]


# # 플래너 모델
# class Plan(BaseModel):
#     steps: List[str] = Field(description="Plan steps")


# # 리플래너 모델
# class Response(BaseModel):
#     response: str


def execute_step(state: PlanExecuteState):
    plan = state["plan"]
    task = plan[0]["reason"]
    # logger.info(state)

    # 실제로는 아래에서 task에 따라 분기하여 실행
    system_message = f"""User ID: "123123123312"
User query: {state["input"]}
Plan: {plan}
Results from past steps: {state["past_steps"] if state["past_steps"] else "None, it's the first step."}
Task of current step: {task}"""
    
    # 툴 선택
    resp = call_pe_tool_v2(
        system_message=system_message,
        messages=[
            HumanMessage(
                content="""Select the most appropriate tool for the user's query at the current stage."""
            )
        ],
        tools=tools,
    )

    # Ollama를 사용할 경우
    # resp = call_ollama(
    #     system_message=system_message,
    #     messages=[
    #         HumanMessage(
    #             content="Select the most appropriate tool for the user's query at the current stage."
    #         )
    #     ],
    #     tools=openai_tools,
    # )

    # logger.info(f"LLM response: {resp.model_dump_json()}")

    tool_calls = resp.additional_kwargs.get("tool_calls", [])
    # 툴 호출
    if tool_calls:
        tool_call = tool_calls[0]
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])

        if tool_name == "prod_meta_search":
            cypher, result = prod_meta_search(tool_args["query"])
            state["product_meta"] = result
            state["cypher"] = cypher
        elif tool_name == "get_service_info":
            result = get_service_info(tool_args["svc_mgmt_num"])
            state["user_info"] = result
        # 현재 버전에서는 위의 두 가지만 사용하도록 되어 있음 (2025-06-18 기준)
        elif tool_name == "get_subscribed_products":
            result = get_subscribed_products(tool_args["svc_mgmt_num"])
            state["user_info"] = result
        elif tool_name == "thinking_tool":
            result = thinking_tool(tool_args["query"], state["past_steps"])
    else:
        result = resp.content
    # past_steps에 기록
    if not result:
        result = "No results found."
    state["past_steps"].append((task, str(result)))
    # plan에서 현재 step 제거
    # state["plan"] = plan[1:]

    return state


def plan_step(state: PlanExecuteState):
    messages = state["messages"]
    system_message = PLANNING_SYS_PROMPT

    llm_response = call_pe_tool_v2(
        system_message=system_message,
        messages=[HumanMessage(content=state["input"])],
        tools=[],
        response_format={"type": "json_object"},
        model_idx=124252,
    )
    
    # Ollama를 사용할 경우
    # llm_response = call_ollama(
    #     system_message=system_message,
    #     messages=[HumanMessage(content=state["input"])],
    #     tools=[],
    #     format="json",
    # )

    try:
        parsed = json.loads(llm_response.content)
        state["plan"] = parsed["plan"]
    except Exception:
        # 혹시 JSON이 아니면, 간단 파싱
        state["plan"] = [llm_response.content]
    
    state["past_steps"] = []
    return state


def replan_step(state: PlanExecuteState):
    # logger.info(state["input"])
    # logger.info(state["plan"])
    # logger.info(state["past_steps"])
    system_message = f"""You are responsible for the Re-plan stage of LangGraph.
Based on the following state, you need to update the plan or generate a final response.

Initial query from user: {state["input"]}

Original plan: {state["plan"]}

Results from previous steps: {state["past_steps"]}

If there are remaining steps, return them as an array. -> {{"plan": [{{"step": 1, "tool": ..., "reason": ...}}, ...]}}
If there are no remaining steps, based on the intial query and the results from previous steps, generate a final response in Korean and return it. -> {{"response": 최종 답변}}
When generating the final response, if there is a markdown table, use its style.

If you re-plan the steps, please return the new plan based on following information.

{PLANNING_SYS_PROMPT}"""

    llm_response = call_pe_tool_v2(
        system_message=system_message,
        messages=[],
        tools=[],
        model_idx=124252,
        response_format={"type": "json_object"},
    )

    # LLM 응답에서 action 파싱
    try:
        parsed = json.loads(llm_response.content)
        if "plan" in parsed:
            state["plan"] = parsed["plan"]
        elif "response" in parsed:
            state["response"] = parsed["response"]
        # if "response" in parsed.get("action", {}):
        #     state["response"] = parsed["action"]["response"]
        # else:
        #     state["plan"] = parsed["action"]["steps"]
    except Exception:
        # 예외 처리
        state["response"] = llm_response.content
    return state


def should_end(state: PlanExecuteState):
    # logger.info(f"Checking if should end: {state.get('response')}")
    return END if state.get("response") else "agent"


workflow = StateGraph(PlanExecuteState)
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_step)
workflow.add_node("replan", replan_step)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "replan")
# workflow.add_conditional_edges("replan", should_end, ["agent", END])
workflow.add_conditional_edges("replan", should_end)
app = workflow.compile()

# inputs = {"input": "5만원 이하 넷플릭스 할인 요금제 알려줘"}


# async def main():
#     async for event in app.astream(inputs):
#         print(event)


# if __name__ == "__main__":
#     asyncio.run(main())
