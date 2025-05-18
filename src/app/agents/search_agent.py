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
from src.app.agents.utils import tool_to_openai_function


tools = [get_service_info, get_subscribed_products, prod_meta_search]
openai_tools = [tool_to_openai_function(t) for t in tools]
openai_tools_json = json.dumps(openai_tools, ensure_ascii=False, indent=2)

print("openai_tools_json>>>>", openai_tools_json)


class PlanExecuteState(TypedDict):
    input: str
    plan: List[str]
    past_steps: Optional[List[Tuple]]
    response: Optional[str]
    user_info: Optional[Dict[str, Any]]
    product_meta: Optional[Dict[str, Any]]
    messages: Annotated[list, add_messages]


# 플래너 모델
class Plan(BaseModel):
    steps: List[str] = Field(description="Plan steps")


# 리플래너 모델
class Response(BaseModel):
    response: str


def message_to_dict(message):
    """Convert various message formats to a standardized dictionary format."""
    if hasattr(message, "to_dict"):
        return message.to_dict()
    elif isinstance(message, dict):
        result = message.copy()
        if "content" not in result:
            result["content"] = ""
        return result
    if message.type.title().lower() == "human":
        role = "user"
        return {"role": role, "content": message.content}
    elif message.type.title().lower() == "ai":
        role = "assistant"
        return {"role": role, "content": message.content}
    elif message.type.title().lower() == "system":
        role = "system"
        return {"role": role, "content": message.content}
    elif message.type.title().lower() == "function" or message.type.title().lower() == "tool":
        role = "assistant"
        return {"role": role, "name": message.name, "content": message.content}
    else:
        print("message.type.title()>>>>", message.type.title())
        raise ValueError("message.type.title()>>>>", message.type.title())


def call_pe_tool_v2(
    messages: list,
    system_message: str,
    tools: list = None,
    model_idx: int = 124252,
    seed=0,
    tool_choice="auto",
    response_format=None,
):
    """
    Call the PE Tool V2 API for chat completions using LangChain's invoke method

    Args:
        messages: Conversation messages
        tools: List of available tools
        model_idx: Model identifier
        seed: Random seed
        tool_choice: Tool selection mode
        response_format: Desired response format

    Returns:
        dict: API response

    Raises:
        ValueError: If API call fails or returns invalid response
    """
    # Process system message same way as in call_pe_tool_v2
    if system_message:
        if len(messages) > 0 and messages[0].type.title().lower() == "system":
            messages[0].content = system_message
        else:
            messages.insert(0, SystemMessage(content=system_message))
    # Serialize messages
    serialized_messages = [message_to_dict(msg) for msg in messages]
    # Prepare model kwargs and options for invoke
    model_kwargs = {}
    invoke_kwargs = {}
    # Handle tools and tool_choice
    if tools:
        model_kwargs["tools"] = tools
        invoke_kwargs["tool_choice"] = tool_choice
    # Handle response_format
    if response_format:
        invoke_kwargs["response_format"] = response_format

    try:
        # Initialize LangChain OpenAI client
        llm = ChatOpenAI(
            base_url="https://aide.dev.apollo-lunar.com/pe-proxy/api/v1/compatible/openai/stream",
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            temperature=0,
            model=str(model_idx),
            api_key="None",
            **model_kwargs,
        )
        # Call API via LangChain with additional parameters
        response = llm.invoke(serialized_messages, **invoke_kwargs)
        return response
    except Exception as e:
        raise ValueError(f"API 오류: {str(e)}")


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
            result = prod_meta_search(tool_args["query"])
            state["product_meta"] = result
        elif tool_name == "get_service_info":
            result = get_service_info(tool_args["svc_mgmt_num"])
            state["user_info"] = result
        elif tool_name == "get_subscribed_products":
            result = get_subscribed_products(tool_args["svc_mgmt_num"])
            state["user_info"] = result

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
    요금제의 경우, 나이 제약 사항이 있을 수 있습니다. 0청년 요금제는 만 34세 이하 고객만 가입 가능합니다. 시니어 요금제는 만 65세 이상 고객만 가입 가능합니다.

    예시:
    "5만원 이하 넷플릭스 할인 요금제 알려줘" -> {{"plan": ["5만원 이하 요금제 찾기", "조회한 요금제 중 넷플릭스 할인 요금제 찾기"]}}
    "내가 가입 가능한 넷플릭스 요금제 알려줘" -> {{"plan": ["고객의 기본 신상정보 조회", "넷플릭스 요금제 조회", "조회된 요금제 중 내가 가입 가능한 요금제 찾기"]}}
    
    json 형식으로 플랜만을 반환해주세요.
    
    """

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
    모두 끝났으면 최종 답변을 생성 후 반환해주세요. -> {{"action": {{"response": "최종 답변"}}}}

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
