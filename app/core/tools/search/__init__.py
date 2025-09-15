from app.core.tools.search.neo4j_search_tool import Neo4jSearchTool
from app.core.tools.search.base import SearchBaseToolKit
from app.core.tools.base import StandardizedTool
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


class SearchToolkitCollectors(ToolKitCollectorProtocol[StandardizedTool]):
    _TOOLKIT_CLASSES: List[Type[SearchBaseToolKit]] = []

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

    def get_valid_tools(self) -> List[StandardizedTool]:
        """사용 가능한 tool 반환"""
        valid_tool_list: List[StandardizedTool] = []
        
        # Neo4j Search Tool 직접 생성
        neo4j_tool = Neo4jSearchTool(
            llm=self.llm,
            llm_embedding=self.llm_embedding,
            neo4j_db=self.graph_db,
            postgres_db=self.postgres_db,
            graphmodel=self.graphmodel,
            vectormodel=self.vectormodel,
            cfg=self.cfg,
        )
        if neo4j_tool.status:
            valid_tool_list.append(neo4j_tool)
            
        return valid_tool_list


__all__ = ["SearchToolkitCollectors"]
