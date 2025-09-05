import uuid
from sqlalchemy import (
    Column,
    String,
    Index,
    Float,
    DateTime,
    text,
    Integer,
    Text,
    Boolean,
    ARRAY,
    UniqueConstraint,
)
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
    __tablename__ = "map_db_vector_store"

    doc_id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    cypher_query = Column(Text, nullable=False)
    query_embedding = Column(Vector(config.vector_store_embedding_model_dims))
    usage_count = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    unknown_num = Column(Integer, default=0)
    unknown_bool = Column(Boolean, default=True)
    unknown_null = Column(Integer, default=0)
    domain_tags = Column(ARRAY(Text))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    __table_args__ = (
        Index("ix_doc_id", "doc_id", "updated_at"),
        UniqueConstraint("query", name="uq_query"),
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
