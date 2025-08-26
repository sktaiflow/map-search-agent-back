from aiohttp import ClientSession, TCPConnector
from dependency_injector import containers, providers
from app.clients.map import MAPClient
from app.clients.synonym import SynonymClient
from app.llms import OpenAIChatLLM, OpenAIEmbeddingModel
from app.clients.http_base import HTTPBaseClient, ClientTimeout, Retry
from openai import AsyncOpenAI
import httpx
import asyncio
from configs import config as global_config


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


async def init_oai_client(
    base_url: str, api_key: str, limits: httpx.Limits, timeout: httpx.Timeout
) -> AsyncOpenAI:
    async with AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        http_client=httpx.AsyncClient(limits=limits, timeout=timeout),
    ) as oai_client:
        yield oai_client
    await asyncio.sleep(0.25)


class ClientContainer(containers.DeclarativeContainer):

    map_api = providers.Factory(
        MAPClient,
        http_client=providers.Resource(
            init_http_client,
            limits=httpx.Limits(
                max_connections=2048, max_keepalive_connections=2048, keepalive_expiry=10
            ),
            timeout=ClientTimeout(connect=0.5, sock_connect=0.5, sock_read=0.5),
            retry=Retry(total=1, base=0.15, cap=0.25),
        ),
        host=global_config.map_base_url,
        api_key=global_config.map_api_key,
    )

    synonym_api = providers.Factory(
        SynonymClient,
        http_client=providers.Resource(
            init_http_client,
            limits=httpx.Limits(
                max_connections=2048, max_keepalive_connections=2048, keepalive_expiry=10
            ),
            timeout=ClientTimeout(connect=0.5, sock_connect=0.5, sock_read=0.5),
            retry=Retry(total=1, base=0.15, cap=0.25),
        ),
        host=global_config.synonym_base_url,
        api_key=global_config.synonym_api_key,
    )

    openai_chat_llm = providers.Factory(
        OpenAIChatLLM,
        base_url=f"{global_config.openai_api_base}/compatible/openai",
        api_key=global_config.openai_api_key,
        model=global_config.llm_model,
        oai_client=providers.Resource(
            init_oai_client,
            base_url=f"{global_config.openai_api_base}/compatible/openai",
            api_key=global_config.openai_api_key,
            limits=httpx.Limits(
                max_keepalive_connections=2048, max_connections=2048, keepalive_expiry=10
            ),
            timeout=httpx.Timeout(pool=1.0, connect=0.5, read=0.5, write=None),
        ),
    )

    embedding_model = providers.Factory(
        OpenAIEmbeddingModel,
        http_client=providers.Resource(
            init_http_client,
            limits=httpx.Limits(
                max_keepalive_connections=2048, max_connections=2048, keepalive_expiry=10
            ),
            timeout=ClientTimeout(connect=1.0, sock_connect=0.5, sock_read=0.5, ceil_threshold=1),
            retry=Retry(total=1, base=0.15, cap=0.25),
        ),
        host=global_config.openai_api_base,
        api_key=global_config.openai_api_key,
        model=global_config.vector_store_embedding_model_name,
    )
