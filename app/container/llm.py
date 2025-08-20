# app/containers/llm.py
from dependency_injector import containers, providers
from langchain_openai import ChatOpenAI
from configs import config as global_config
from llms.embedding_llm import EmbeddingClient
from llms.llm import LLMClient, _default_headers
from langchain_openai import OpenAIEmbeddings
from configs import config as global_config


class LLMContainer(containers.DeclarativeContainer):

    headers_provider = providers.Callable(_default_headers)

    chat_singleton = providers.Singleton(
        ChatOpenAI,
        base_url=global_config.openai_api_base,
        api_key=global_config.openai_api_key,
        # timeout/headers는 per-call로 주입
    )
    llm_client = providers.Factory(
        LLMClient,
        chat_factory=chat_singleton,
        headers_provider=headers_provider,
        max_retries=1,
    )

    embeddings_singleton = providers.Singleton(
        OpenAIEmbeddings,
        api_key=global_config.openai_api_key,
        base_url=global_config.openai_api_base,
        # model/dimensions는 호출부에서 per-call 지정
    )
    embed_client = providers.Factory(
        EmbeddingClient,
        embeddings_factory=embeddings_singleton,
        default_model=global_config.vector_store_embedding_model_name,
        default_dimensions=global_config.vector_store_embedding_model_dims,  # 필요 시 1536 등 지정
        normalize=True,  # 벡터 정규화 운영 정책
    )
