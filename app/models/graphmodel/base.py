from __future__ import annotations

from typing import Any, Mapping, Optional, Dict, Any, LiteralString, List, Union

from utils.logger import logger
from utils.decorators import neo4j_session_required

from neo4j import AsyncSession, AsyncManagedTransaction, Query, ResultSummary

from abc import abstractmethod

from neo4j import Query as Neo4jQuery
from app.database.neo4j import Neo4jDatabase


class BaseAsyncGraphModel:

    @neo4j_session_required("r")
    async def asession_read(
        self,
        *,
        session: Optional[AsyncSession] = None,
        cypher: Union[str, Neo4jQuery, LiteralString],
        params: Optional[Mapping[str, Any]] = None,
    ) -> list[Any]:
        res = await session.run(cypher, params or {})
        return [r async for r in res]

    @neo4j_session_required("r")
    async def execute_read_tx(
        self,
        *,
        session: Optional[AsyncSession] = None,
        cypher: Union[LiteralString, str, Neo4jQuery],
        params: Optional[Mapping[str, Any]] = None,
    ) -> list[Any]:

        async def work(tx: AsyncManagedTransaction):
            res = await tx.run(cypher, params or {})
            return [r async for r in res]

        return await session.execute_read(work)

    @neo4j_session_required("w")
    async def execute_write(
        self,
        *,
        session: Optional[AsyncSession] = None,
        cypher: Union[str, Neo4jQuery, LiteralString],
        params: Optional[Mapping[str, Any]] = None,
    ) -> ResultSummary:
        async def work(tx: AsyncManagedTransaction) -> ResultSummary:
            res = await tx.run(cypher, params or {})
            return await res.consume()

        return await session.execute_write(work)

    @abstractmethod
    def get_schema(cls) -> str:
        """Return the schema of the Graph database"""

    @abstractmethod
    def get_structured_schema(cls) -> Dict[str, Any]:
        """Return the schema of the Graph database"""
        ...

    @classmethod
    @abstractmethod
    def refresh_schema(cls) -> None:
        """Refresh the graph schema information."""


# class BaseGraphModel:
#     """
#     NEO4J 를 직접 핸들링할떄 필요한 베이스 모델
#     Read만 권장합니다. - Read할 경우 transaction 이용한 Read 권장
#     """

#     _session_ctx: ContextVar[AsyncSession | None] = ContextVar("neo4j_session", default=None)

#     @classmethod
#     def set_session(cls: Type[_T], session: AsyncSession) -> Token:
#         return cls._session_ctx.set(session)

#     @classmethod
#     def get_session(cls) -> AsyncSession:
#         session = cls._session_ctx.get()
#         if session is None:
#             raise RuntimeError("Neo4j session is not set in ContextVar.")
#         return session

#     @classmethod
#     def reset_session(cls: Type[_T], token: Token) -> None:
#         cls._session_ctx.reset(token)

#     @classmethod
#     @abstractmethod
#     def _extract_cypher(cls, content: str) -> str:
#         """cypher 파싱 코드"""

#     @classmethod
#     @neo4j_session_required
#     async def asession_read(
#         cls,
#         session: AsyncSession,
#         cypher: Union[str, Query],
#         params: Optional[Mapping[str, Any]] = None,
#     ) -> Any:
#         """session으로 cypher read하는 함수"""
#         params = params or {}
#         result = await session.run(cypher, params or {})
#         rows = []
#         async for r in result:
#             rows.append(r)
#         return rows

#     @classmethod
#     @neo4j_session_required
#     async def execute_read_tx(
#         cls,
#         cypher: str,
#         session: AsyncSession,
#         *,
#         params: Optional[dict[str, Any]] = None,
#     ):
#         """
#         읽기 전용: 트랜잭션 함수(자동 재시도) 안에서 실행.
#         대량 결과면 스트리밍/페이징 전략을 별도 메서드로 분리해도 좋음.
#         """

#         async def work(tx: AsyncManagedTransaction):
#             res = await tx.run(cypher, params or {})
#             return [r async for r in res]

#         return await session.execute_read(work)

#     @classmethod
#     @neo4j_session_required
#     async def execute_write(
#         cls,
#         cypher: str,
#         session: AsyncSession,
#         *,
#         params: Optional[dict[str, Any]] = None,
#     ):
#         """
#         쓰기 전용: 트랜잭션 함수(자동 재시도) 안에서 실행.
#         반환값: ResultSummary (consume 결과) 또는 필요시 바꿔도 됨.
#         """

#         async def work(tx: AsyncManagedTransaction):
#             res = await tx.run(cypher, params or {})
#             return await res.consume()

#         return await session.execute_write(work)

#     @classmethod
#     @abstractmethod
#     def get_schema(cls) -> str:
#         """Return the schema of the Graph database"""

#     @classmethod
#     @abstractmethod
#     def get_structured_schema(cls) -> Dict[str, Any]:
#         """Return the schema of the Graph database"""
#         ...

#     @classmethod
#     @abstractmethod
#     def refresh_schema(cls) -> None:
#         """Refresh the graph schema information."""
