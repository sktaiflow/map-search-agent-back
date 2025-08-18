import asyncio
import attr
import random
import json


from aiohttp import (
    ClientTimeout,
    ServerTimeoutError,
    ClientSession,
    ClientError,
)
from typing import Optional, List, Literal, Dict
import aiohttp
from aiohttp.typedefs import LooseHeaders
from multidict import CIMultiDictProxy


# TODO map 서비스 레이턴시 기준 나오면 수정 필요
@attr.s(auto_attribs=True, frozen=True, slots=True)
class Retry:
    """
    - full: Full Jitter (AWS 권장)
    - equal: Equal Jitter (변동성 절충)
    """

    total: int = 2
    base: float = 0.3
    cap: float = 0.75
    retry_on_status: List[int] = attr.Factory(list)
    retry_on_read_timeout: bool = False

    def full_jitter(self, attempts: int) -> float:
        """
        기본 aws 권장 재시도 전략 -> 최대 분산시 가장 좋음
        """
        exp = self.base * (2**attempts)
        upper = min(self.cap, exp)
        return random.random() * upper

    def equal_jitter(self, attempts: int) -> float:
        t = min(self.cap, self.base * (2**attempts))
        return (t / 2.0) + (random.random() * (t / 2.0))

    def backoff(
        self,
        attempts: int,
        strategy: Literal["full", "equal"] = "full",
        prev_sleep: Optional[float] = None,
    ) -> float:
        """
        통합 진입점:
        - attempts: 0부터 시작하는 재시도 회수
        - strategy: 'full' | 'equal'
        """
        if strategy == "full":
            return self.full_jitter(attempts)
        elif strategy == "equal":
            return self.equal_jitter(attempts)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")


class InvalidHttpStatus(Exception):
    def __init__(self, status: int, body: bytes) -> None:
        super().__init__(f"HttpStatus={status} Body={body.decode()}")
        self.status = status
        self.body = body


class HTTPBaseClientResponse:
    def __init__(self, status: int, headers: CIMultiDictProxy[str], body: bytes) -> None:
        self.status = status
        self.headers = headers
        self.body = body
        self._json = None

    def json(self):
        if self._json is None:
            self._json = json.loads(self.body)
        return self._json

    def text(self, encoding="utf-8", errors="strict") -> str:
        return self.body.decode(encoding, errors)


class HTTPBaseClient:
    def __init__(
        self,
        session: Optional[ClientSession] = None,
        timeout: Optional[ClientTimeout] = None,
        retry: Optional[Retry] = None,
    ) -> None:
        self._session = session
        self.timeout = timeout or ClientTimeout(connect=0.5, sock_connect=1, sock_read=3)
        self.retry = retry or Retry()
        self._owns_session = session is None  # (외부주입인지 체크)

    @property
    def session(self) -> ClientSession:
        """
        현재 ClientSession 반환.
        - 세션이 없거나 이미 닫혔으면 새로 생성
        """
        if self._session is None or self._session.closed:
            self._session = ClientSession(timeout=self.timeout)
        return self._session

    async def __aenter__(self):
        _ = self.session
        return self

    async def __aexit__(self, exc_type, exc_val, traceback):
        await self.close()

    async def close(self):
        if self._owns_session and self._session is not None and not self._session.closed:
            await self._session.close()

    async def request(
        self,
        method: str,
        url: str,
        timeout: Optional[ClientTimeout] = None,
        **kwargs,
    ) -> HTTPBaseClientResponse:

        for attempts in range(self.retry.total + 1):
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    timeout=(timeout or self.timeout),
                    **kwargs,
                ) as resp:
                    body = await resp.read()
                    if self.retry.retry_on_status and resp.status in self.retry.retry_on_status:
                        raise InvalidHttpStatus(resp.status, body)
                return HTTPBaseClientResponse(resp.status, resp.headers, body)

            except asyncio.CancelledError:
                raise

            except asyncio.TimeoutError as e:
                # 읽기/연결 타임아웃 재시도 여부
                if not self.retry.retry_on_read_timeout or attempts >= self.retry.total:
                    raise

                await asyncio.sleep(self.retry.backoff(attempts))

            except InvalidHttpStatus as e:
                if attempts < self.retry.total:
                    await asyncio.sleep(self.retry.backoff(attempts))
                else:
                    raise

            except ClientError as e:
                if attempts < self.retry.total:
                    await asyncio.sleep(self.retry.backoff(attempts))
                else:
                    raise

            except Exception:
                raise


def build_http_client(
    session: ClientSession, timeout: ClientTimeout, retry: Retry
) -> "HTTPBaseClient":
    return HTTPBaseClient(session=session, timeout=timeout, retry=retry)
