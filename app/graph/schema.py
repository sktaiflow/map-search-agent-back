from dataclasses import dataclass
from typing import Any, List, Dict
from pydantic import BaseModel, Field
from app.database.postgresql import PostgreSQLDatabase
from app.models.vectorstore.base import BaseModel as PGVectorModel


@dataclass(frozen=True)
class Deps:
    llm_client: Any
    embed_client: Any
    neo4j_client: Any
    postgres_db: PostgreSQLDatabase
    pgvector_models: list[PGVectorModel]
    toolkit: Any
    tools: Any


class Plan(BaseModel):
    plan: List[Dict[str, Any]] = Field(..., description="플랜")


class PastStep(BaseModel):
    task: str
    tool: str
    query: Dict[str, Any]
    result: Any
    result_metadata: Dict[str, Any]
