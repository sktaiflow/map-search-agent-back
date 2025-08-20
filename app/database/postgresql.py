import asyncio
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.asyncio import AsyncEngine
from typing import AsyncIterator
from app.models.vectorstore.base import BaseModel as PGVectorBaseModel
from contextlib import asynccontextmanager


class PostgreSQLEngineConfig(BaseModel):
    url: str
    echo: bool
    pool_size: int
    max_overflow: int
    pool_timeout: int
    pool_recycle: int
    pool_pre_ping: bool


class PostgreSQLDatabase:
    def __init__(self, engine_config: PostgreSQLEngineConfig):
        self.engine: AsyncEngine = create_async_engine(
            engine_config.url,
            echo=engine_config.echo,
            pool_size=engine_config.pool_size,
            max_overflow=engine_config.max_overflow,
            pool_timeout=engine_config.pool_timeout,
            pool_recycle=engine_config.pool_recycle,
            pool_pre_ping=engine_config.pool_pre_ping,
        )
        self.session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    @asynccontextmanager
    async def get_async_session(self) -> AsyncIterator[AsyncSession]:
        if self.session_maker is None:
            raise RuntimeError("Session maker is not initialized.")
        async with self.session_maker() as session:
            context_token = PGVectorBaseModel.set_session(session)
            try:
                yield session
            except (asyncio.CancelledError, asyncio.TimeoutError):
                if session and (session.in_transaction() or session.get_transaction() is not None):
                    await session.rollback()
                raise
            finally:
                PGVectorBaseModel.reset_session(context_token)
