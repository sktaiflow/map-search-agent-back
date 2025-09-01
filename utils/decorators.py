from functools import wraps
from typing import Optional, Callable, Awaitable, Any
from neo4j import AsyncSession


def session_required(fn):
    @wraps(fn)
    async def wrapper(self_or_cls, session=None, *args, **kwargs):
        if session is None:
            session = self_or_cls.get_session()
        return await fn(self_or_cls, session, *args, **kwargs)

    return wrapper


def neo4j_session_required(
    _fn: Callable[..., Awaitable[Any]] | None = None, *, access_mode: str = "r"
):
    """
    사용법:
      @session_required(access_mode="r") : access_mode 기본값은 "r": READ 나머진 Write 모드
      async def foo(self, ..., session: AsyncSession | None = None): ...

    동작:
      - session이 전달되면 그대로 사용 (닫는 주체 외부)
      - session이 없으면 self.get_session(mode)로 새 세션을 열고 async with로 close (닫는 주체: decorator)

    % 단 single server 환경에서 bolt driver는 access 모드 부하 분산 작동안함 -> 문법적으로 지원은 하지만, cluster 처럼 효과는 없음
    """

    def decorator(fn: Callable[..., Awaitable[Any]]):
        @wraps(fn)
        async def wrapper(self_or_cls, *args, **kwargs):
            session: Optional[AsyncSession] = kwargs.get("session")
            if session is not None:
                return await fn(self_or_cls, *args, **kwargs)

            if not hasattr(self_or_cls, "get_session"):
                raise RuntimeError("get_session(mode) 메서드를 self에 구현해야 합니다.")

            session = self_or_cls.get_session(access_mode)
            kwargs["session"] = session
            return await fn(self_or_cls, *args, **kwargs)

        return wrapper

    return decorator if _fn is None else decorator(_fn)


def neo4j_tx_required(_fn: Callable[..., Awaitable[Any]] | None = None, *, access_mode: str = "r"):
    """
    사용법:
      @tx_required(access_mode="r") Transaction 처리의 경우 session.execute_read 혹은 session.execute_write로 사용
      async def get_user(self, user_id: str, *, tx=None): ...

      % 단 single server 환경에서 bolt driver는 access 모드 부하 분산 작동안함 -> 문법적으로 지원은 하지만, cluster 처럼 효과는 없음
    """

    def decorator(fn: Callable[..., Awaitable[Any]]):
        @wraps(fn)
        async def wrapper(self_or_cls, *args, **kwargs):
            if kwargs.get("tx") is not None:
                return await fn(self_or_cls, *args, **kwargs)

            if not hasattr(self_or_cls, "get_session"):
                raise RuntimeError("get_session(mode) 메서드를 self에 구현하세요.")

            async with self_or_cls.get_session() as session:
                executor = session.execute_read if access_mode == "r" else session.execute_write

                async def work(tx):
                    return await fn(self_or_cls, *args, **{**kwargs, "tx": tx})

                return await executor(work)

        return wrapper

    return decorator if _fn is None else decorator(_fn)
