import os
from typing import Any, ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict

from utils.enums import StrEnum


class StackType(StrEnum):
    PRD = "prd"
    STG = "stg"
    DEV = "dev"
    LOCAL = "local"


class BaseConfig(BaseSettings):
    api_description: ClassVar[
        str
    ] = """
        """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = os.environ.get("APP_NAME", "map-search-agent")
    stack_type: str = os.environ.get("STACK_TYPE", StackType.LOCAL)
    healthcheck_url: str = os.environ.get("HEALTHCHECK_URL", "/api/healthcheck")

    api_version: str = "no_version_specified"
    app_version: str = "0.0.1"

    # llm
    llm_model: str = "gpt-4o"
    fast_llm_model: str = "gpt-4o-mini"
    reasoning_llm_model: str = "gpt-o3"

    # map api config
    map_base_url: str = ""
    map_api_key: str = ""

    map_method_api_key_plan_add_on: str = ""
    map_method_api_key_plan_basic: str = ""
    map_method_api_key_contract_mobile: str = ""

    # synonym api config
    synonym_base_url: str = ""
    synonym_api_key: str = ""

    # pg vector store config
    vector_store_collection_name: str = "map-vector-store"
    vector_store_provider: str = "pgvector"
    vector_store_dbname: str = "map_db_vector_store"
    vector_store_embedding_model_name: str = "text-embedding-3-small"
    vector_store_embedding_model_dims: int = 1536
    vector_store_diskann: bool = False
    vector_store_hnsw: bool = True

    postgres_db_host: str = ""
    postgres_db_port: int = 5432
    postgres_db_username: str = ""
    postgres_db_password: str = ""

    # pg vector
    m: int = 16
    ef_construction: int = 64

    # smart bee
    openai_api_base: str = ""
    openai_api_key: str = ""
    aws_region: str = "ap-northeast-2"

    # neo4j
    neo4j_nlb_dns: str = ""
    neo4j_bolt_port: str = "7687"
    neo4j_username: str = ""
    neo4j_password: str = ""
