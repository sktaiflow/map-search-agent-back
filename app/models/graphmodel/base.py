from __future__ import annotations

from typing import Any, Mapping, Optional, Type, TypeVar
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, update, inspect
from sqlalchemy import Column, DateTime, func, delete
from sqlalchemy.dialects.postgresql import insert
from typing import Optional, Type, TypeVar, List
from sqlalchemy import text
from contextvars import ContextVar, Token


from datetime import datetime, timedelta, timezone
from utils.logger import logger
from utils.decorators import neo4j_session_required, neo4j_tx_required
from neo4j import Result, AsyncTransaction, AsyncSession

from langchain.chains import GraphCypherQAChain

_T = TypeVar("_T", bound="BaseGraphModel")

Base = declarative_base()


class BaseGraphModel(Base):
    """
    NEO4J 를 직접 핸들링할떄 필요한 베이스 모델
    Read만 권장합니다. - Read할 경우 transaction 이용한 Read 권장
    """

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
    @neo4j_session_required(access_mode="r")
    async def asession_read(
        cls, session: AsyncSession, cypher: str, params: Optional[Mapping[str, Any]] = None
    ) -> Any:
        """session으로 cypher read하는 함수"""
        params = params or {}
        result = await session.run(cypher, params or {})
        rows = []
        async for r in result:
            rows.append(r)
        return rows

    @classmethod
    @neo4j_tx_required(access_mode="r")
    async def execute_read_tx(
        cls,
        cypher: str,
        *,
        tx: Optional[AsyncTransaction] = None,
        params: Optional[dict[str, Any]] = None,
    ):
        """
        읽기 전용: 트랜잭션 함수(자동 재시도) 안에서 실행.
        대량 결과면 스트리밍/페이징 전략을 별도 메서드로 분리해도 좋음.
        """
        res = await tx.run(cypher, params or {})
        rows = []
        async for r in res:
            rows.append(r)
        return rows

    @classmethod
    @neo4j_tx_required(access_mode="w")
    async def execute_write(
        cls,
        cypher: str,
        *,
        params: Optional[dict[str, Any]] = None,
        tx: Optional[AsyncTransaction] = None,
    ):
        """
        쓰기 전용: 트랜잭션 함수(자동 재시도) 안에서 실행.
        반환값: ResultSummary (consume 결과) 또는 필요시 바꿔도 됨.
        """
        res = await tx.run(cypher, params or {})
        summary = await res.consume()
        return summary

    # TODO: 추후 검토 후 고도화 혹은 수정 필요, 테스트 필요: 어떤 값들을 schema string으로 Return하는지 확인 필요
    @classmethod
    @neo4j_session_required(access_mode="r")
    async def _get_schema_str(
        cls,
        *,
        session: Optional[AsyncSession] = None,
        timeout: float = 5.0,
        apoc_limit: int = 20,
        sample_node_limit: int = 3,
    ) -> str:
        """
        PROMPT에 넣을 스키마 문자열 생성.
        - APOC이 있으면 apoc.meta.schema() 결과 일부를 우선 활용
        - 없거나 실패하면 labels / relationshipTypes / propertyKeys로 요약
        - 샘플 노드의 라벨/키 형태도 조금 덧붙임
        """
        lines: List[str] = ["# Graph Schema (summary)"]

        # 1) APOC meta.schema 시도
        try:
            apoc_q = """
                CALL apoc.meta.schema()
                YIELD * RETURN * LIMIT $lim
            """
            apoc_res = await session.run(apoc_q, {"lim": apoc_limit}, timeout=timeout)
            apoc_rows = []
            async for r in apoc_res:
                apoc_rows.append(str(dict(r)))
            if apoc_rows:
                lines.append(f"APOC meta.schema sample (limit {apoc_limit}):")
                lines.extend(apoc_rows)
                return "\n".join(lines)
        except Exception:
            lines.append("(APOC meta.schema 사용 불가, fallback 사용)")

        labels_q = "CALL db.labels() YIELD label RETURN label"
        rels_q = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        props_q = "CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey"

        labels_res = await session.run(labels_q, timeout=timeout)
        rels_res = await session.run(rels_q, timeout=timeout)
        props_res = await session.run(props_q, timeout=timeout)

        labels = sorted([r["label"] for r in [r async for r in labels_res]])  # type: ignore[index]
        rels = sorted([r["relationshipType"] for r in [r async for r in rels_res]])  # type: ignore[index]
        props = sorted([r["propertyKey"] for r in [r async for r in props_res]])  # type: ignore[index]

        label_list = ", ".join(labels) if labels else "(none)"
        rel_list = ", ".join(rels) if rels else "(none)"
        prop_list = ", ".join(props) if props else "(none)"

        lines.extend(
            [
                f"Labels: {label_list}",
                f"Relationships: {rel_list}",
                f"PropertyKeys: {prop_list}",
            ]
        )

        # 3) 샘플 노드 형태 (labels, keys)
        sample_q = """
        MATCH (n)
        WITH labels(n) AS ls, keys(n) AS ks
            RETURN ls AS labels, ks AS keys
        LIMIT $lim
        """
        sample_res = await session.run(sample_q, {"lim": sample_node_limit}, timeout=timeout)
        sample = [r async for r in sample_res]
        if sample:
            lines.append(f"Sample node shapes (labels, keys) — {sample_node_limit} rows:")
            for s in sample:
                lines.append(f"- {s.get('labels')} / {s.get('keys')}")

        return "\n".join(lines)
