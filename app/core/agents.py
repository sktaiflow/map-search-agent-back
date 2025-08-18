import json
import time
from typing import Any, AsyncIterator
from uuid import UUID, uuid4

from langchain_core.runnables import RunnableConfig
from opentelemetry import trace
from pydantic import BaseModel

from app.core.graph import BaseGraph
from app.schemas import ChatMessage, InvokeRequest
from utils import logger
from utils.chat import langchain_to_chat_message

# from langgraph.pregel.io import AddableValuesDict

DEFAULT_ALLOWED_EVENTS: list[tuple[str, str]] = [
    ("LangGraph", "on_chain_end"),
]


class BaseAgentConfig(BaseModel):
    agent_name: str
    allowed_events: list[tuple[str, Any]] = DEFAULT_ALLOWED_EVENTS


class BaseAgent:
    """
    모든 Agent의 공통 기능을 제공하는 베이스 클래스
    """

    config: BaseAgentConfig = BaseAgentConfig(agent_name="base-agent")

    def __init__(self, graph: BaseGraph) -> None:
        self.graph = graph

    def invoke(self, input_data: dict[str, Any]) -> Any:
        """일반 실행 방식"""
        return self.graph.compiled_graph.invoke(input_data)

    def postprocess_input(self, user_input: InvokeRequest) -> tuple[dict[str, Any], UUID]:
        run_id = uuid4()
        thread_id = user_input.thread_id or str(uuid4())
        checkpoint_id = str(uuid4())
        kwargs = {
            "input": {
                "id": user_input.id,
                # "messages": [HumanMessage(content=user_input.user_message)],
                "user_message": user_input.user_message,
                "thread_id": thread_id,
            },
            "config": {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                },
            },
            "run_id": run_id,
        }
        return kwargs

    async def postprocess_messages(self, content: str) -> ChatMessage:
        """
        graph 의 invoke 결과를 가공하고자 할 때 사용합니다.

        Args:
            content: graph 의 invoke 결과

        Returns:
            ChatMessage: 가공된 메시지
        """
        chat_message = langchain_to_chat_message(content.get("messages", [])[-1])

        return chat_message

    async def ainvoke(self, input_data: dict[str, Any], runnable_config: RunnableConfig):
        """
        graph 의 invoke 를 호출하고, 결과를 전달할때 사용.

        Args:
            input_data (dict[str, Any]): _description_

        Returns:
            Any: _description_
        """
        runnable_config["recursion_limit"] = 50
        try:
            invoke_result = await self.graph.compiled_graph.ainvoke(
                input=input_data, config=runnable_config
            )
        except Exception as e:
            logger.error("Error ainvoking graph", exc_info=e)
            raise

        content = invoke_result
        # content = await self.postprocess_messages(invoke_result)
        return content
