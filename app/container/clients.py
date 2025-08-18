from aiohttp import ClientSession, TCPConnector
from dependency_injector import containers, providers
from app.clients.map import MAPClient
from app.clients.http_base import HTTPBaseClient, ClientTimeout, Retry
import httpx
import asyncio


async def init_http_client(limits: httpx.Limits, timeout: ClientTimeout, retry: Retry):
    async with ClientSession(
        connector=TCPConnector(
            limit=limits.max_connections,
            limit_per_host=limits.max_keepalive_connections,
            keepalive_timeout=limits.keepalive_expiry,
        )
    ) as session:
        yield HTTPBaseClient(session=session, timeout=timeout, retry=retry)
    await asyncio.sleep(0.25)


class ClientContainer(containers.DeclarativeContainer):
    settings = providers.Dependency()
    config = providers.Configuration()

    http_client = providers.Resource(
        init_http_client,
        limits=httpx.Limits(
            max_connections=2048, max_keepalive_connections=2048, keepalive_expiry=10
        ),
        timeout=ClientTimeout(connect=0.5, sock_connect=0.5, sock_read=0.5),
        retry=Retry(total=1, base=0.15, cap=0.25),
    )
    # HTTP 클라이언트 (서비스별로 session 주입)
    map_client = providers.Factory(
        MAPClient,
        http_client=http_client,
        host=settings.provided.map_base_url,
        api_key=settings.provided.map_api_key,
    )
