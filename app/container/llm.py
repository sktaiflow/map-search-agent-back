# app/containers/llm.py
from dependency_injector import containers, providers
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from configs import config as global_config
from app.llms.embedding_llm import EmbeddingClient
from app.llms.llm import LLMClient, _default_headers


class LLMContainer(containers.DeclarativeContainer):

    # TODO: smartbee 사용시 url suffix 추가
    chat_singleton = providers.Singleton(
        ChatOpenAI,
        base_url=f"{global_config.openai_api_base}/compatible/openai",
        api_key=global_config.openai_api_key,
    )

    llm_client = providers.Factory(
        LLMClient,
        chat_factory=chat_singleton,
        max_retries=1,
    )

    # TODO: smartbee 사용시 url suffix 추가
    embeddings_singleton = providers.Singleton(
        OpenAIEmbeddings,
        base_url=f"{global_config.openai_api_base}",
        api_key=global_config.openai_api_key,
    )
    embed_client = providers.Factory(
        EmbeddingClient,
        embeddings_factory=embeddings_singleton,
        default_model=global_config.vector_store_embedding_model_name,
        default_dimensions=global_config.vector_store_embedding_model_dims,  # 필요 시 1536 등 지정
        normalize=True,  # 벡터 정규화 운영 정책
    )
