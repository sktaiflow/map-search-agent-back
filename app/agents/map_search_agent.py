from app.agents.base import BaseAgent, BaseAgentConfig
from typing import Any, Dict, List
from uuid import UUID
from app.schemas.api.schema import InvokeRequest, InvokeResponse, SynonymsRequest, SynonymsResponse
from app.graph.base import BaseGraph
from app.clients.synonym import SynonymClient
from app.models.vectorstore.base import BaseModel as PGVectorModel
from app.agents.task.analyzer import (
    split_query,
    concat_query,
    preprocess_synonyms,
    retrieval_query,
)
from app.graph.states import OutputState
from app import logger
from langchain_core.runnables import RunnableConfig


class MapSearchAgentConfig(BaseAgentConfig):
    pass


# TODO: sysnonym 호출할 포인트가 바뀌면 그에따라 변경 필요
class MapSearchAgent(BaseAgent):
    def __init__(self, http_client: SynonymClient, graph: BaseGraph) -> None:
        self.http_client = http_client
        super().__init__(graph)

    config = MapSearchAgentConfig(agent_name="map-search-agent")

    async def preprocess(
        self, user_input: InvokeRequest, request_params: Dict[str, Any] = {}
    ) -> InvokeRequest:
        """동의어 API 호출 필요"""

        return user_input

    async def ainvoke(
        self, input_data: InvokeRequest, runnable_config: RunnableConfig
    ) -> InvokeResponse:
        """
        graph 의 invoke 를 호출하고, 결과를 전달할때 사용.

        Args:
            input_data (dict[str, Any]): _description_

        Returns:
            Any: _description_
        """
        runnable_config["recursion_limit"] = 50

        try:
            input_data = await self.preprocess(input_data)
            graph_result = await self.graph.compiled_graph.ainvoke(
                input=input_data, config=runnable_config
            )
            content = self.postprocess(graph_result)
            return content

        except Exception as e:
            logger.error("Error ainvoking graph", exc_info=e)
            raise e

    def postprocess(self, response: OutputState) -> InvokeResponse:
        if response.return_type == 1:
            response_data = {
                "raw_result": response.raw_data,
                "product_meta": response.product_meta,  # 이미 ID 리스트로 처리됨
                "user_info": response.user_info_data,
            }
        else:
            response_data = {
                "insights": response.insights,
                "summary": response.summary,
                "reasoning": response.reasoning,
                "raw_result": response.raw_data,
                "product_meta": response.product_meta,
                "user_info": response.user_info_data,
                "updated_at": response.updated_at,
            }

        return InvokeResponse(
            code=200,
            data=response_data or {},
        )
