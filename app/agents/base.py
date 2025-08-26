from pydantic import BaseModel
from app import logger
from app.graph.base import BaseGraph
from app.schemas.api.schema import InvokeRequest

from langchain_core.runnables import RunnableConfig
from abc import abstractmethod
from typing import Any
from uuid import UUID, uuid4
from abc import abstractmethod


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

    @abstractmethod
    def postprocess_input(self, user_input: InvokeRequest) -> tuple[dict[str, Any], UUID]:
        pass

    @abstractmethod
    async def postprocess_messages(self, content: str):
        """
        graph 의 invoke 결과를 가공하고자 할 때 사용합니다.
        Args:
            content: graph 의 invoke 결과
        Returns:
            가공된 메시지
        """
