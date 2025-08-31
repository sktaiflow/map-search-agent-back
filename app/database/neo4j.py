# app/db/neo4j_database.py
from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Sequence
from contextvars import ContextVar

from neo4j import AsyncGraphDatabase, AsyncDriver

# from neo4j.async_.work import AsyncSession  # type: ignore

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


class Neo4jEngineConfig(BaseModel):
    uri: str
    user: str
    password: str
    max_connection_pool_size: int = 50
    connection_timeout: float = 1.0
    fetch_size: int = Field(
        default=10,
        description="결과를 스트리밍 받는 단위 크기 (너무 크면 메모리 위험 작으면 속도 저하) ",
        ge=1,
        le=1000,
    )
    keep_alive: bool = True
    liveness_check_timeout: float | None = 5.0
    connection_acquisition_timeout: float = 1.0
    max_transaction_retry_time: float = 5.0
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
            asyncio.Semaphore(max_concurrent_sessions) if max_concurrent_sessions else None
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
            fetch_size=fetch_size or self._cfg.fetch_size,
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
                database=database,
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
