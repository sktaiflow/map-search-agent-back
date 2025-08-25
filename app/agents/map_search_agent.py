from app.agents.base import BaseAgent, BaseAgentConfig
from typing import Any, Dict, List
from uuid import UUID
from app.schemas.api.schema import InvokeRequest, SynonymsRequest, SynonymsResponse
from app.graph.base import BaseGraph
from app.clients.synonym import SynonymClient
from app.models.vectorstore.base import BaseModel as PGVectorModel
from app.agents.task.analyzer import (
    split_query,
    concat_query,
    preprocess_synonyms,
    retrieval_query,
)
from app.graph.states import InputState


class MapSearchAgentConfig(BaseAgentConfig):
    pass


# TODO: sysnonym 호출할 포인트가 바뀌면 그에따라 변경 필요
class MapSearchAgent(BaseAgent):
    def __init__(self, http_client: SynonymClient, graph: BaseGraph) -> None:
        self.http_client = http_client
        super().__init__(graph)

    config = MapSearchAgentConfig(agent_name="map-search-agent")

    # TODO: 명세서 json, data, params 어떤건지 확인 필요 (개발 명세서 불확실 ex): "application-json", "application-x-www-form-urlencoded" ...)
    async def get_synonyms(self, params: Dict[str, Any]) -> tuple[Dict, Dict]:
        """synonym 호출"""
        resp = await self.http_client._request("POST", "/kvf/multi-keywords", json=params)
        return (params, resp.json())

    def preprocess_synonyms(self, keywords: List[str], synonyms: Dict[str, Any]) -> str:
        """동의어 프롬프트 결과를 만들어 사용할 f string 결과 반환"""
        synonyms_list = synonyms.get("resultList", [])
        if synonyms_list:
            synonyms_entity_list = [synonym.get("entityName") for synonym in synonyms_list]
            return f"""동의어 사전: {keywords}: {synonyms_entity_list}"""
        else:
            return ""

    async def apreprocess_input(
        self, user_input: InvokeRequest, request_params: Dict[str, Any] = {}
    ) -> str:
        """문장합치고 -> 자르고 -> 동의어 호출로 변경 -> 결과 반환"""
        query = concat_query(user_input.query)
        splitted_query = split_query(query)
        # TODO: 동의어 API 명세서: keywords -> 갯수 제한 [3-5] 고려하는 로직 필요
        params = {
            "utterance": query,
            "keywords": splitted_query,
            "searchOption": request_params.get("searchOption", "1"),
            "threshold": request_params.get("threshold", "30"),
        }
        # SynonymsRequest.model_validate(params)
        params, synonyms = await self.get_synonyms(params)
        # TODO: 동의어 호출 처리
        synonyms_template = self.preprocess_synonyms(params.get("keywords", []), synonyms)

        ## query + synonyms_template
        return query + "\n" + synonyms_template

    async def apreprocess_input_mock(self, user_input: InvokeRequest):
        query = concat_query(user_input.query)
        return query

    # TODO: 포스트 프로세싱
    async def postprocess_messages(self, response):
        return response
