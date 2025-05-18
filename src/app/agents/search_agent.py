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
from src.app.tools import get_service_info, get_subscribed_products, prod_meta_search
from src.app.agents.utils import tool_to_openai_function, call_pe_tool_v2
from langchain_neo4j import Neo4jGraph

tools = [get_service_info, get_subscribed_products, prod_meta_search]
openai_tools = [tool_to_openai_function(t) for t in tools]
openai_tools_json = json.dumps(openai_tools, ensure_ascii=False, indent=2)

user_search_tools = [get_service_info, get_subscribed_products]
user_search_tools_json = [tool_to_openai_function(t) for t in user_search_tools]

graph = Neo4jGraph(
        url="bolt://neo4j-gds-apoc-n10s:7687",  #"bolt://localhost:7687",
        username="neo4j",
        password="neo4jpassword",
        # enhanced_schema=True,
        sanitize=True,  # 연결 검증
    )


class PlanExecuteState(TypedDict):
    input: str
    plan: List[str]
    past_steps: Optional[List[Tuple]]
    response: Optional[str]
    user_info: Optional[Dict[str, Any]]
    product_meta: Optional[Dict[str, Any]]
    messages: Annotated[list, add_messages]
    cypher: Optional[str]

# 플래너 모델
class Plan(BaseModel):
    steps: List[str] = Field(description="Plan steps")


# 리플래너 모델
class Response(BaseModel):
    response: str



gpt4o_llm = ChatOpenAI(
    model="123974",  # gpt-4o-0513
    openai_api_key="NONE",
    openai_api_base="https://aide.dev.apollo-lunar.com/pe-proxy/api/v1/compatible/openai",
    streaming=False,
)

planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "유저 쿼리를 여러 단계의 plan으로 분해하세요. 각 단계는 독립적으로 실행 가능해야 하며, 불필요한 단계는 추가하지 마세요.",
        ),
        ("placeholder", "{messages}"),
    ]
)

replanner_prompt = ChatPromptTemplate.from_template(
    """
유저 쿼리: {input}
기존 플랜: {plan}
수행한 단계: {past_steps}
남은 단계가 있으면 plan을, 모두 끝났으면 response를 반환하세요.
"""
)


def execute_step(state: PlanExecuteState):
    plan = state["plan"]
    task = plan[0]
    # 실제로는 아래에서 task에 따라 분기하여 실행

    system_message = f"""
    유저 쿼리: {state["input"]}
    플랜: {plan}
    전 단계 결과: {state["past_steps"] if state["past_steps"] else "없음, 첫 단계임"}
    현재 수행할 단계: {task}
    """
    print("system_message>>>>", system_message)
    # 툴 호출
    resp = call_pe_tool_v2(
        system_message=system_message,
        messages=[
            HumanMessage(
                content="현재 수행할 단계에 맞게 유저의 요청사항에 맞는 tool을 선택해 주세요."
            )
        ],
        tools=openai_tools,
        model_idx=124252,
    )
    print("resp>>>>", resp)
    tool_calls = resp.additional_kwargs.get("tool_calls", [])
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
        elif tool_name == "get_subscribed_products":
            result = get_subscribed_products(tool_args["svc_mgmt_num"])
            state["user_info"] = result
    else:
        result = resp.content
    print("result>>>>", result)
    # past_steps에 기록
    if not result:
        result = "조회 결과 없음"
    state["past_steps"].append((task, str(result)))
    # plan에서 현재 step 제거
    # state["plan"] = plan[1:]
    return state


def plan_step(state: PlanExecuteState):
    messages = state["messages"]
    system_message = f"""유저 쿼리를 여러 단계의 plan으로 분해하세요. 각 단계는 독립적으로 실행 가능해야 하며, 불필요한 단계는 추가하지 마세요.
    
    Domain mapping and other rules::
    - "무제한"과 관련있는 값은 전부 999999로 치환하였음
    - 나이 제약 사항이 있는 요금제 -> 나이 비교 검색 필요
    
    상품 검색 시에 활용가능한 graph schema는 아래와 같습니다.
    {graph.schema}

    유저 정보에 대한 조회는 다음 방법으로 할 수 있어
    {user_search_tools_json}
    
    예시:
    "5만원 이하 넷플릭스 할인 요금제 알려줘" -> {{"plan": ["계획 1", "계획 2"]}}
    
    json 형식으로 플랜만을 반환해주세요.
    
    """
    print("system_message>>>>", system_message)
    llm_response = call_pe_tool_v2(
        system_message=system_message,
        messages=[HumanMessage(content=state["input"])],
        tools=[],
        model_idx=124252,
        response_format={"type": "json_object"},
    )

    try:
        parsed = json.loads(llm_response.content)
        state["plan"] = parsed["plan"]
    except Exception:
        # 혹시 JSON이 아니면, 간단 파싱
        state["plan"] = [llm_response.content]
    state["past_steps"] = []
    return state


def replan_step(state: PlanExecuteState):

    system_message = f"""
    유저 쿼리: {state["input"]}
    기존 플랜: {state["plan"]}
    수행한 단계: {state["past_steps"]}
    
    남은 단계가 있으면 스텝들을 배열로 반환해주세요. -> {{"action": {{"steps": ["남은 단계"]}}}}
    모두 끝났으면 최종 답변을 생성 후 반환해주세요. 유저는 중간 답변을 보지 않고 최종 답변만 보게 됩니다. -> {{"action": {{"response": "최종 답변"}}}}

    json 형식으로 반환해주세요.
    """

    print("system_message>>>>", system_message)
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
        if "response" in parsed.get("action", {}):
            state["response"] = parsed["action"]["response"]
        else:
            state["plan"] = parsed["action"]["steps"]
    except Exception:
        # 예외 처리
        state["response"] = llm_response.content
    return state


def should_end(state: PlanExecuteState):
    return END if state.get("response") else "agent"


workflow = StateGraph(PlanExecuteState)
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_step)
workflow.add_node("replan", replan_step)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "replan")
workflow.add_conditional_edges("replan", should_end, ["agent", END])

app = workflow.compile()

inputs = {"input": "5만원 이하 넷플릭스 할인 요금제 알려줘"}


async def main():
    async for event in app.astream(inputs):
        print(event)


if __name__ == "__main__":
    asyncio.run(main())
