from __future__ import annotations

from typing import Any, Mapping, Optional, Type, TypeVar
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, update, inspect
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import Column, DateTime, func, delete
from sqlalchemy.dialects.postgresql import insert
from typing import Optional, Type, TypeVar
from sqlalchemy import text
from contextvars import ContextVar, Token


from datetime import datetime, timedelta, timezone
from utils.logger import logger
from utils.decorators import session_required
from neo4j import Result

from langchain.chains import GraphCypherQAChain

_T = TypeVar("_T", bound="BaseGraphModel")

Base = declarative_base()


class BaseGraphModel(Base):
    """NEORJ 를 직접 핸들링할떄 필요한 베이스 모델"""

    __abstract__ = True
    _session_ctx: ContextVar[AsyncSession | None] = ContextVar("neo4j_session", default=None)

    @classmethod
    def set_session(cls: Type[_T], session: AsyncSession) -> Token:
        return cls._session_ctx.set(session)

    @classmethod
    def get_session(cls) -> AsyncSession:
        session = cls._session_ctx.get()
        if session is None:
            raise RuntimeError("Neo4j session is not set in ContextVar.")
        return session

    @classmethod
    def reset_session(cls: Type[_T], token: Token) -> None:
        cls._session_ctx.reset(token)

    @classmethod
    @session_required
    async def aread(
        cls: Type[_T],
        session: AsyncSession,
        cypher: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> list[dict]:
        """
        READ 트랜잭션에서 Cypher 실행.
        LangGraph/Tool 등 어디서든 재사용 가능.
        """
        params = params or {}

        def _work(tx):  # tx: AsyncTransaction
            return tx.run(cypher, params)

        result: Result = await session.execute_read(_work)
        rows = [r.data() for r in await result.to_list()]
        return rows

    @classmethod
    @session_required
    async def awrite(
        cls: Type[_T],
        session: AsyncSession,
        cypher: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> list[dict]:
        """
        WRITE 트랜잭션에서 Cypher 실행.
        """
        params = params or {}

        def _work(tx):
            return tx.run(cypher, params)

        result: Result = await session.execute_write(_work)
        rows = [r.data() for r in await result.to_list()]
        return rows

    # TODO: 추후 검토 후 고도화 혹은 수정 필요, 테스트 필요: 어떤 값들을 schema string으로 Return하는지 확인 필요
    async def _get_schema_str(self) -> str:
        """
        PROMPT에 넣을 스키마 문자열 생성.
        - 라벨/관계타입/프로퍼티키를 모아 프롬프트에 넣기 좋은 텍스트로 변환
        - APOC이 있으면 apoc.meta.schema를 우선 시도
        """
        schema_lines = ["# Graph Schema (summary)"]

        try:
            # 1) APOC meta schema 시도
            apoc_schema = await self.run_read("CALL apoc.meta.schema() YIELD * RETURN * LIMIT 20")
            if apoc_schema:
                schema_lines.append("APOC meta.schema sample (limited 20 rows):")
                for row in apoc_schema:
                    schema_lines.append(str(row))
                return "\n".join(schema_lines)
        except Exception as e:
            schema_lines.append(f"(APOC meta.schema 사용 불가, fallback)")

        # 2) Fallback: 기본 시스템 프로시저
        labels = await self.run_read("CALL db.labels() YIELD label RETURN label")
        rels = await self.run_read(
            "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        )
        props = await self.run_read("CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey")

        label_list = ", ".join(sorted([r["label"] for r in labels]))
        rel_list = ", ".join(sorted([r["relationshipType"] for r in rels]))
        prop_list = ", ".join(sorted([r["propertyKey"] for r in props]))

        schema_lines.extend(
            [
                f"Labels: {label_list or '(none)'}",
                f"Relationships: {rel_list or '(none)'}",
                f"PropertyKeys: {prop_list or '(none)'}",
            ]
        )

        # 샘플 노드 모양
        sample_nodes = await self.run_read(
            """
            MATCH (n) WITH labels(n) AS ls, keys(n) AS ks LIMIT 3
            RETURN ls AS labels, ks AS keys
            """
        )
        if sample_nodes:
            schema_lines.append("Sample node shapes (labels, keys):")
            for s in sample_nodes:
                schema_lines.append(f"- {s['labels']} / {s['keys']}")

        return "\n".join(schema_lines)
