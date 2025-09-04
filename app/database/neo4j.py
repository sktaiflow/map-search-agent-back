# app/db/neo4j_database.py
from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Sequence
from contextvars import ContextVar

from neo4j import AsyncGraphDatabase, AsyncDriver

from app import logger

from pydantic import BaseModel, Field
from app.models.graphmodel.base import BaseGraphModel
from neo4j import (
    AsyncGraphDatabase,
    AsyncDriver,
    AsyncSession,
    AsyncTransaction,
    READ_ACCESS,
    WRITE_ACCESS,
)


# TODO: session params 최적화 필요
class Neo4jEngineConfig(BaseModel):
    uri: str
    user: str
    password: str
    max_concurrent_sessions: int = 70
    max_connection_pool_size: int = 100
    connection_timeout: float = 1.0
    keep_alive: bool = True
    liveness_check_timeout: float | None = 5.0
    connection_acquisition_timeout: float = 1.0
    max_transaction_retry_time: float = (
        5.0  # 최대 트랜잭션 재시도 시간 (서비스 사용성에 맞게 맞춰야함)
    )
    max_connection_lifetime: int = 1800  # pool TCP 커넥션 재사용 시간
    initial_retry_delay: float = 0.5
    retry_delay_multiplier: float = 2.0
    retry_delay_jitter_factor: float = 0.3


class Neo4jDatabase:
    """
    - DI로 주입된 AsyncDriver를 사용
    """

    def __init__(
        self,
        driver: AsyncDriver,
        engine_config: Neo4jEngineConfig,
        *,
        max_concurrent_sessions: Optional[int] = None,
        default_database: Optional[str] = None,
    ):
        self._driver = driver
        self._cfg = engine_config
        self._default_db = default_database
        self._sema: Optional[asyncio.Semaphore] = (
            asyncio.Semaphore(max_concurrent_sessions)
            if max_concurrent_sessions
            else None  # connection pool > self._sema -> 안그러면 병목
        )

    def open_session(
        self,
        *,
        mode: str = "r",
        database: Optional[str] = None,
        impersonated_user: Optional[str] = None,
        fetch_size: Optional[int] = None,
        bookmarks: Optional[Sequence[str]] = None,  # ← 추가
    ) -> AsyncSession:
        access = READ_ACCESS if mode == "r" else WRITE_ACCESS
        return self._driver.session(
            default_access_mode=access,
            database=database,
            bookmarks=bookmarks,
            impersonated_user=impersonated_user,
            fetch_size=fetch_size or 1000,  # (내부 로직 봐보니 default 값이 1000)
        )

    @asynccontextmanager
    async def get_async_session(
        self,
        *,
        mode: str = "r",
        database: Optional[str] = None,
        impersonated_user: Optional[str] = None,
        fetch_size: Optional[int] = None,
        bookmarks: Optional[Sequence[str]] = None,
    ) -> AsyncIterator[AsyncSession]:
        if self._sema:
            await self._sema.acquire()
        try:
            async with self.open_session(
                mode=mode,
                database=database or "neo4j",
                impersonated_user=impersonated_user,
                fetch_size=fetch_size,
                bookmarks=bookmarks,
            ) as session:
                context_token = BaseGraphModel.set_session(session)
                try:
                    yield session
                finally:
                    BaseGraphModel.reset_session(context_token)
        finally:
            if self._sema:
                self._sema.release()
