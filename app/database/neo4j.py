# app/db/neo4j_database.py
from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from contextvars import ContextVar

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.async_.work import AsyncSession  # type: ignore

from app import logger

from pydantic import BaseModel, Field
from app.models.graphmodel.base import BaseGraphModel


class Neo4jEngineConfig(BaseModel):
    uri: str
    user: str
    password: str
    max_pool_size: int = 50
    connection_timeout: float = 2.0
    fetch_size: int = Field(
        default=10,
        description="결과를 스트리밍 받는 단위 크기 (너무 크면 메모리 위험 작으면 속도 저하) ",
        ge=1,
        le=1000,
    )


class Neo4jDatabase:
    """
    - Driver 풀 생성/종료 관리
    - 세션 생성/반납 관리(get_async_session)
    """

    def __init__(self, engine_config: Neo4jEngineConfig):
        self._cfg = engine_config
        self._driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        if self._driver:
            return
        self._driver = AsyncGraphDatabase.driver(
            self._cfg.uri,
            auth=(self._cfg.user, self._cfg.password),
            max_connection_pool_size=self._cfg.max_pool_size,
            connection_timeout=self._cfg.connection_timeout,
        )

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @asynccontextmanager
    async def get_async_session(self) -> AsyncIterator[AsyncSession]:
        if not self._driver:
            raise RuntimeError("Neo4j driver is not initialized. Call connect() first.")

        async with self._driver.session(fetch_size=self._cfg.fetch_size) as session:
            token = BaseGraphModel.set_session(session)
            try:
                yield session
            except (asyncio.CancelledError, asyncio.TimeoutError):
                # neo4j는 execute_read/write가 트랜잭션을 관리하므로 명시 롤백은 보통 불필요
                # 명시 트랜잭션을 쓴 경우엔 여기서 session.begin_transaction() 핸들링 가능
                raise
            finally:
                BaseGraphModel.reset_session(token)
