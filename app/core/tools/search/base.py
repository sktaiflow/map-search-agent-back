from typing import Type, List, Optional, Dict, Any, Union
from app import logger
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError, Field
from app.core.tools.utils import SafeValidationTool
from abc import ABC, abstractmethod

from app.database.neo4j import Neo4jDatabase
from app.models.graphmodel.graph import AsyncGraphModel
from app.llms.llm_http import OpenAIChatLLM
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from configs import config as global_config
from configs.default import BaseConfig
from app.database.postgresql import PostgreSQLDatabase
from app.models.vectorstore.semantic_retrieval import SemanticSearchModel
from app.llms.embedding_llm_http import OpenAIEmbeddingModel


class SearchBaseToolKit:
    """neo4j Search 관련 도구들을 관리하는 기본 툴킷 클래스"""

    def __init__(
        self,
        llm: OpenAIChatLLM,
        graphmodel: AsyncGraphModel,
        graph_db: Neo4jDatabase,
        postgres_db: PostgreSQLDatabase,
        vectormodel: SemanticSearchModel,
        llm_embedding: OpenAIEmbeddingModel,
        cfg: BaseConfig,
    ):
        self.llm = llm
        self.graphmodel = graphmodel
        self.graph_db = graph_db
        self.postgres_db = postgres_db
        self.vectormodel = vectormodel
        self.llm_embedding = llm_embedding
        self.cfg = cfg or global_config

    @abstractmethod
    def tools(self) -> List[SafeValidationTool]:
        """모든 tool 반환"""

    @abstractmethod
    def valid_tools(self) -> List[SafeValidationTool]:
        """사용 가능한 tool 반환"""
