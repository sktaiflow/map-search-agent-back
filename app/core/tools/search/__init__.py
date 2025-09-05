from app.core.tools.search.graph_tool import GraphSearchToolKit
from app.core.tools.search.base import SearchBaseToolKit
from app.core.tools.utils import SafeValidationTool
from langchain_core.utils.function_calling import convert_to_openai_function
from typing import Any, Dict, List, Type, Optional, Union

from app.database.neo4j import Neo4jDatabase
from app.models.graphmodel.graph import AsyncGraphModel
from app.llms.llm_http import OpenAIChatLLM
from app.core.tools.protocol import ToolKitCollectorProtocol
from langchain_neo4j import Neo4jGraph
from app.database.postgresql import PostgreSQLDatabase
from app.models.vectorstore.semantic_retrieval import SemanticSearchModel
from app.llms.embedding_llm_http import OpenAIEmbeddingModel
from configs.default import BaseConfig
from configs import config as global_config

from app import logger


class SearchToolkitCollectors(ToolKitCollectorProtocol[SafeValidationTool]):
    _TOOLKIT_CLASSES: List[Type[SearchBaseToolKit]] = [GraphSearchToolKit]

    def __init__(
        self,
        llm: OpenAIChatLLM,
        graph_db: Neo4jDatabase,
        graphmodel: Union[AsyncGraphModel, Neo4jGraph],
        postgres_db: PostgreSQLDatabase,
        vectormodel: SemanticSearchModel,
        llm_embedding: OpenAIEmbeddingModel,
        cfg: Optional[BaseConfig] = None,
    ):
        self.llm = llm
        self.graph_db = graph_db
        self.graphmodel = graphmodel
        self.postgres_db = postgres_db
        self.vectormodel = vectormodel
        self.llm_embedding = llm_embedding
        self.cfg = cfg or global_config

    def get_valid_tools(self) -> List[SafeValidationTool]:
        """사용 가능한 tool 반환"""
        valid_tool_list: List[SafeValidationTool] = []
        for toolkit_class in self._TOOLKIT_CLASSES:
            tools = toolkit_class(
                self.llm,
                self.graphmodel,
                self.graph_db,
                self.postgres_db,
                self.vectormodel,
                self.llm_embedding,
                self.cfg,
            ).valid_tools()
            valid_tool_list.extend([tool for tool in tools if isinstance(tool, SafeValidationTool)])
        return valid_tool_list


__all__ = ["SearchToolkitCollectors"]
