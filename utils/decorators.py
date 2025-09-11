from functools import wraps
from typing import Optional, Callable, Awaitable, Any, ClassVar, Literal
from neo4j import AsyncSession
from contextvars import ContextVar, Token
from app import logger


def session_required(fn):
    @wraps(fn)
    async def wrapper(self_or_cls, session=None, *args, **kwargs):
        if session is None:
            session = self_or_cls.get_session()
        return await fn(self_or_cls, session, *args, **kwargs)

    return wrapper


class SessionContext:
    _ctx: ClassVar[ContextVar[AsyncSession | None]] = ContextVar("neo4j_session", default=None)

    @classmethod
    def set(cls, session: AsyncSession) -> Token[AsyncSession | None]:
        return cls._ctx.set(session)

    @classmethod
    def get(cls) -> AsyncSession:
        s = cls._ctx.get()
        if s is None:
            raise RuntimeError("Neo4j session is not set in ContextVar.")
        return s

    @classmethod
    def reset(cls, token: Token[AsyncSession | None]) -> None:
        cls._ctx.reset(token)


def neo4j_session_required(mode: Literal["r", "w"] = "r"):
    def deco(fn):
        @wraps(fn)
        async def wrapper(self, *args, session: Optional[AsyncSession] = None, **kwargs):
            if session is not None:
                return await fn(self, *args, session=session, **kwargs)
            try:
                s = SessionContext.get()
                return await fn(self, *args, session=s, **kwargs)
            except RuntimeError as e:
                logger.error("Neo4j session is not set in ContextVar.", exc_info=e)

        return wrapper

    return deco


"""
Deprecated old decorators [수정하였음 혹시나 해서 남겨둠]
def neo4j_session_read(fn: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
    @wraps(fn)
    async def wrapper(self_or_cls: Any, *args, **kwargs) -> R:
        session: Optional[AsyncSession] = kwargs.get("session")
        if session is None:
            if not hasattr(self_or_cls, "get_session"):
                raise RuntimeError("get_session() must be implemented.")
            kwargs["session"] = self_or_cls.get_session()
        return await fn(self_or_cls, *args, **kwargs)

    return wrapper


def neo4j_write_tx(fn: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
    @wraps(fn)
    async def wrapper(self_or_cls: Any, *args, **kwargs) -> R:
        if kwargs.get("tx") is not None:
            return await fn(self_or_cls, *args, **kwargs)

        if not hasattr(self_or_cls, "get_session"):
            raise RuntimeError("get_session() must be implemented.")

        async with self_or_cls.get_session() as session:

            async def work(tx):
                return await fn(self_or_cls, *args, **{**kwargs, "tx": tx})

            return await session.execute_write(work)

    return wrapper
"""
