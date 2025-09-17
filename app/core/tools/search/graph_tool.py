import json
from typing import Any, Dict, List, Optional, Sequence, Type, Union

from langchain_core.tools import ArgsSchema, BaseTool
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

from configs import config as global_config
from configs.default import BaseConfig
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph

from app.core.prompts import CYPHER_GENERATION_PROMPT
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
    vectormodel: type[SemanticSearchModel]
    cfg: BaseConfig

    def _run(self, query: str) -> str:
        raise NotImplementedError(
            "이 도구는 비동기 실행만 지원합니다. _arun을 사용하세요."
        )

    async def _generate_cypher(
        self,
        query: str,
        fewshot_examples: str,
        *,
        database: Optional[str] = None,
        access_mode: str = "r",
    ) -> Dict[str, Any] | None:

        async with self.neo4j_db.get_async_session(
            mode=access_mode,
            database=database,
        ) as session:
            graph_schema = await self.graphmodel.get_schema(session=session)
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

        if not llm_response.message:
            return None

        try:
            return json.loads(llm_response.message)
        except json.JSONDecodeError:
            return {"cypher": llm_response.message.strip()}

    async def _execute_cypher(
        self,
        cypher: str,
        params: Dict[str, Any] | None = None,
        *,
        database: Optional[str] = None,
        access_mode: str = "r",
    ) -> Any:
        async with self.neo4j_db.get_async_session(
            mode=access_mode,
            database=database,
        ) as session:
            return await self.graphmodel.execute_read_tx(
                session=session,
                cypher=cypher,
                params=params or {},
            )

    async def _embed_query(self, query: str) -> List[float]:
        embedding_obj = await self.llm_embedding.aembed(query)
        return embedding_obj.embeddings[0]

    async def _retrieve_fewshot_examples(
        self, embedding: List[float], limit: int = 3
    ) -> List[Dict[str, Any]]:
        async with self.postgres_db.get_async_session() as session:
            retrieved_examples = await self.vectormodel.asearch_by_vector(
                session=session,
                embedding=embedding,
                limit=limit,
                similarity_cutoff=0.0,
            )

        examples: List[Dict[str, Any]] = []
        for record, score in retrieved_examples:
            question = getattr(record, "query", None)
            cypher = getattr(record, "cypher_query", None)
            if question and cypher:
                examples.append(
                    {
                        "question": question,
                        "cypher": cypher,
                        "score": score,
                    }
                )
        return examples

    async def _arun(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        access_mode: str = "r",
    ) -> Dict[str, Any]:
        params = params or {}
        fewshot_payload = "[]"

        try:
            embedding = await self._embed_query(query)
            examples = await self._retrieve_fewshot_examples(embedding)
        except Exception as exc:  # noqa: BLE001
            logger.warn(
                message="fewshot 예시 생성에 실패했습니다.",
                exc_info=exc,
                type="fewshot",
            )
            examples = []

        if examples:
            fewshot_payload = json.dumps(examples, ensure_ascii=False)

        try:
            generated = await self._generate_cypher(
                query,
                fewshot_payload,
                database=database,
                access_mode=access_mode,
            )
            if not generated:
                raise ValueError("Cypher generation failed")

            cypher_query = generated.get("cypher") or generated.get("query")
            if not cypher_query:
                raise ValueError("생성된 결과에서 cypher 구문을 찾지 못했습니다.")

            generated_params = generated.get("params") or {}
            merged_params = {**generated_params, **params}

            cypher_result = await self._execute_cypher(
                cypher_query,
                merged_params,
                database=database,
                access_mode=access_mode,
            )

            return {
                "cypher": cypher_query,
                "params": merged_params,
                "result": cypher_result,
                "fewshot_examples": examples,
                "input_query": query,
            }

        except Exception as error:  # noqa: BLE001
            logger.error(message=f"Cypher search error: {error}", exc_info=error)
            raise


class CypherQAChainTool(SafeValidationTool):
    """Neo4j Cypher 쿼리를 실행하는 도구"""

    name: str = "CypherSearchTool"
    description: str = (
        "자연어 쿼리를 Cypher로 변환하여 Neo4j 그래프 데이터베이스를 검색합니다"
    )
    args_schema: Type[BaseModel] = CypherRequest
    response_model: Type[BaseModel] = CypherResponse
    status: bool = False
    agent: GraphCypherQAChain
    cfg: BaseConfig

    def _run(self, query: str) -> str:
        raise NotImplementedError(
            "이 도구는 비동기 실행만 지원합니다. _arun을 사용하세요."
        )

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
        vectormodel: type[SemanticSearchModel],
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
