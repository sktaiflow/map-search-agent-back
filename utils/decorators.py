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


def neo4j_session_required(*, access_mode: str = "r"):
    """
    사용법:
      @session_required(access_mode="r")
      async def foo(self, ..., session: AsyncSession | None = None): ...

    동작:
      - session이 전달되면 그대로 사용 (닫는 주체 외부)
      - session이 없으면 self.get_session(mode)로 새 세션을 열고 async with로 close (닫는 주체: decorator)
    """

    def decorator(fn: Callable[..., Awaitable[Any]]):
        @wraps(fn)
        async def wrapper(self, *args, **kwargs):
            session: Optional[AsyncSession] = kwargs.get("session")
            if session is not None:
                return await fn(self, *args, **kwargs)

            if not hasattr(self, "get_session"):
                raise RuntimeError("get_session(mode) 메서드를 self에 구현해야 합니다.")

            async with self.get_session(mode=access_mode) as s:
                kwargs["session"] = s
                return await fn(self, *args, **kwargs)

        return wrapper

    return decorator


def neo4j_tx_required(*, access_mode: str = "r"):
    """
    사용법:
      @tx_required(access_mode="r")
      async def get_user(self, user_id: str, *, tx=None): ...
    """

    def decorator(fn: Callable[..., Awaitable[Any]]):
        @wraps(fn)
        async def wrapper(self, *args, **kwargs):
            # 외부에서 tx를 넘겨주면 그대로 사용 (닫지 않음)
            if kwargs.get("tx") is not None:
                return await fn(self, *args, **kwargs)

            if not hasattr(self, "get_session"):
                raise RuntimeError("get_session(mode) 메서드를 self에 구현하세요.")

            async with self.get_session(mode=access_mode) as session:  # 우리가 열었으니 여기서 닫힘
                executor = session.execute_read if access_mode == "r" else session.execute_write

                async def work(tx):
                    return await fn(self, *args, **{**kwargs, "tx": tx})

                return await executor(work)

        return wrapper

    return decorator
