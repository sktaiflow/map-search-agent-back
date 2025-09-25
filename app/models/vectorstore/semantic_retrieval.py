import uuid
from typing import TypeVar

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    delete,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vectorstore.base import BaseModel
from configs import config
from utils.decorators import session_required

_T = TypeVar("_T", bound="BaseModel")


class SemanticSearchModel(BaseModel):
    __tablename__ = "map_db_vector_store"

    # --- 기존 컬럼 (유지) ---
    doc_id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    cypher_query = Column(Text, nullable=False)
    query_embedding = Column(Vector(config.vector_store_embedding_model_dims))
    usage_count = Column(Integer, default=0)
    domain_tags = Column(ARRAY(Text))
    quality_score = Column(Float, default=1.0)
    success_rate = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False, onupdate=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        Index("ix_doc_id", "doc_id", "updated_at"),
    )

    @classmethod
    @session_required
    async def asearch_by_vector_orm(
        cls, session: AsyncSession, embeddings: list[float], limit: int = 3
    ):
        vector_column = getattr(cls, "query_embedding")
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