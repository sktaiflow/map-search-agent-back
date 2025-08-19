import aioboto3

from aioboto3.resources.base import ServiceResource
from aiobotocore.client import BaseClient
from dependency_injector import containers, providers
from typing import AsyncGenerator


async def init_postgres_client(
    session: aioboto3.Session, endpoint_url: str = None
) -> AsyncGenerator[BaseClient, None]:
    client = await session.client("dynamodb", endpoint_url=endpoint_url).__aenter__()
    yield client
    await client.__aexit__(None, None, None)
