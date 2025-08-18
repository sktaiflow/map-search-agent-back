from aiohttp import ClientSession, TCPConnector
from dependency_injector import containers, providers
from app.clients.map import MAPClient
from app.clients.http_base import HTTPBaseClient


async def init_aiohttp_session():
    connector = TCPConnector(limit=100, limit_per_host=20)
    return ClientSession(connector=connector)


class ClientContainer(containers.DeclarativeContainer):
    settings = providers.Dependency()
    config = providers.Configuration()

    session: providers.Resource[ClientSession] = providers.Resource(init_aiohttp_session)
    # HTTP 클라이언트 (서비스별로 session 주입)
    http_client = providers.Factory(
        HTTPBaseClient,
        session=session,
        base_url=config.foo_base_url,
    )
    map_client = providers.Factory(
        MAPClient,
        host=settings.provided.map_base_url,
        api_key=settings.provided.map_api_key,
        http_client=http_client,
    )
