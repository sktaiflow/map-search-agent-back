import json
from typing import Any, List, Type, Union, Optional

from langchain_core.tools import BaseTool, ArgsSchema
from pydantic import BaseModel, Field

from app.core.tools.utils import SafeValidationTool
from app.core.tools.search.base import SearchBaseToolKit
from app.schemas.cypher import CypherRequest, CypherResponse

from app.llms.llm_http import OpenAIChatLLM
from app.llms.embedding_llm_http import OpenAIEmbeddingModel
from app.database.neo4j import Neo4jDatabase
from app.models.graphmodel.graph import AsyncGraphModel
from app.models.vectorstore.semantic_retrieval import SemanticSearchModel
from app import logger

from typing import Dict, Sequence
from configs.default import BaseConfig
from configs import config as global_config
from app.core.prompts import CYPHER_GENERATION_PROMPT
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from app.database.postgresql import PostgreSQLDatabase


# TODO: 로직이 현재 불명확해서 백프로 구현이 어려움 -> 툴의 기능단위가 명확해지면 필요 없는 자원 제거 필요
"""
불명확 포인트: 툴의 기능 scope
CASE 1. embedding + fewshot retrieval +  generation + cypher execution 
CASE 2. cypher  generation + cypher execution 
CASE 3. cypher execution 
"""


class CypherRunTool(SafeValidationTool):
    """Neo4j Cypher 쿼리를 실행하는 도구"""

    name: str = "ProductMetaSearchTool"
    description: str = (
        "자연어 쿼리를 Cypher로 변환하여 그래프 데이터베이스에서 상품 메타 정보를 검색합니다"
    )
    args_schema: Type[BaseModel] = CypherRequest
    response_model: Type[BaseModel] = CypherResponse
    status: bool = True
    llm: OpenAIChatLLM
    llm_embedding: OpenAIEmbeddingModel
    neo4j_db: Neo4jDatabase
    postgres_db: PostgreSQLDatabase
    graphmodel: AsyncGraphModel
    vectormodel: SemanticSearchModel
    cfg: BaseConfig

    def _run(self, query: str) -> str:
        raise NotImplementedError("이 도구는 비동기 실행만 지원합니다. _arun을 사용하세요.")

    async def _generate_cypher(self, query: str, fewshot_examples: str) -> str | None:

        graph_schema = await self.graphmodel.get_schema()
        prompt = CYPHER_GENERATION_PROMPT.partial(
            schema=graph_schema, question=query, fewshot_examples=fewshot_examples
        )

        system_message = prompt.format()

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": query},
        ]

        llm_response = await self.llm.agenerate_response(
            messages=messages,
            model=self.cfg.llm_model,
            temperature=0.0,
            max_tokens=500,
            response_format={"type": "json_object"},
            seed=0,
        )
        return llm_response.message

    async def _execute_cypher(self, cypher: str, params: dict = {}) -> str:
        return await self.graphmodel.execute_read_tx(cypher=cypher, params=params)

    async def _embed_query(self, query: str) -> List[float]:
        embedding_obj = await self.llm_embedding.aembed(query)
        return embedding_obj.embeddings[0]

    async def _retrieve_fewshot_examples(self, embedding: List[float]) -> List[str]:
        async with self.postgres_db.get_async_session() as session:
            retrieved_examples = await self.vectormodel.asearch_by_vector(
                session=session, embedding=embedding, similarity_cutoff=0.0
            )
        return retrieved_examples

    async def _arun(self, query: str, params: dict = {}, fewshot_examples: str = "") -> str:
        try:
            cypher_query = await self._generate_cypher(query, fewshot_examples)
            # TODO 없으면 어떡할지 구현 필요
            if not cypher_query:
                raise ValueError("Cypher generation failed")

            cypher_result = await self._execute_cypher(cypher_query, params)
            return cypher_result

        except Exception as e:
            logger.error(message=f"Cypher search error: {e}", exc_info=e)
            raise e


class CypherQAChainTool(SafeValidationTool):
    """Neo4j Cypher 쿼리를 실행하는 도구"""

    name: str = "CypherSearchTool"
    description: str = "자연어 쿼리를 Cypher로 변환하여 Neo4j 그래프 데이터베이스를 검색합니다"
    args_schema: Type[BaseModel] = CypherRequest
    response_model: Type[BaseModel] = CypherResponse
    status: bool = False
    agent: GraphCypherQAChain
    cfg: BaseConfig

    def _run(self, query: str) -> str:
        raise NotImplementedError("이 도구는 비동기 실행만 지원합니다. _arun을 사용하세요.")

    # TODO 아직 미완성 코드 (구현후 사용하려면 status 값 바꾸기 -> 이부분 제대로 쓰려면 Neo4jGraph 사용할떄 driver config도 전부 지정 필요함 (안그럼 터집니다.)
    async def _arun(self, query: str, params: dict = {}) -> str:
        resp = await self.agent.ainvoke({"query": query})
        result_json = json.dumps(resp["result"], ensure_ascii=False, indent=2)
        return result_json


class GraphSearchToolKit(SearchBaseToolKit):

    name: str = "GraphSearchToolKit"
    description: str = "Graph 이용한 Search Tool 모아두는 Toolkit"

    def __init__(
        self,
        llm: OpenAIChatLLM,
        graphmodel: Union[AsyncGraphModel, Neo4jGraph],
        graph_db: Neo4jDatabase,
        postgres_db: PostgreSQLDatabase,
        vectormodel: SemanticSearchModel,
        llm_embedding: OpenAIEmbeddingModel,
        cfg: Optional[BaseConfig] = None,
    ):
        self.llm = llm
        self.graphmodel = graphmodel
        self.graph_db = graph_db
        self.postgres_db = postgres_db
        self.vectormodel = vectormodel
        self.llm_embedding = llm_embedding
        self.cfg = cfg or global_config

    def valid_tools(self) -> List[SafeValidationTool]:
        """사용 가능한 tool 반환"""
        all_tools = [
            CypherRunTool(
                llm=self.llm,
                neo4j_db=self.graph_db,
                graphmodel=self.graphmodel,
                postgres_db=self.postgres_db,
                vectormodel=self.vectormodel,
                llm_embedding=self.llm_embedding,
                cfg=self.cfg,
            ),
        ]
        return [tool for tool in all_tools if tool.status]

    def tools(self) -> Sequence[SafeValidationTool]:
        """모든 tool 반환"""
        raise NotImplementedError("This method is not implemented")
