import uuid
from sqlalchemy import Column, String, Index, Float
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import select, delete
from typing import TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vectorstore.base import BaseModel
from configs import config
from utils.decorators import session_required

_T = TypeVar("_T", bound="BaseModel")


class SemanticSearchModel(BaseModel):
    __tablename__ = "semantic_search_store"

    doc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vector = Column(Vector(config.vector_store_embedding_model_dims))
    agent_id = Column(String(100), nullable=True)
    relevance_score = Column(Float, nullable=True)

    __table_args__ = (Index("ix_user_id_memory_type", "user_id", "memory_type", "updated_at"),)

    @classmethod
    @session_required
    async def asearch_by_vector_orm(
        cls, session: AsyncSession, embeddings: list[float], limit: int = 3
    ):
        vector_column = getattr(cls, "vector")
        distance = vector_column.cosine_distance(embeddings).label("score")

        stmt = select(cls, distance).order_by(distance).limit(limit)
        execute_result = await session.execute(stmt)

        return execute_result.all()

    @classmethod
    @session_required
    async def get_all_docs(cls, session: AsyncSession) -> list[str]:
        stmt = select(cls.doc_id)
        execute_result = await session.execute(stmt)
        return execute_result.scalars().all()
