import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar, Any

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
        env_file=f".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = os.environ.get("APP_NAME", "map-search-agent")
    stack_type: StackType = os.environ.get("STACK_TYPE", StackType.LOCAL)

    api_version: str = "no_version_specified"

    # llm
    llm_model: str = "gpt-4o"

    # map api config
    map_base_url: str = ""
    map_api_key: str = ""

    map_method_api_key_contract_mobile_device: str
    map_method_api_key_account_payment: str
    map_method_api_key_plan_benefit: str
    map_method_api_key_rate_usage: str
    map_method_api_key_data_refill: str
    map_method_api_key_contract_customer: str
    map_method_api_key_plan_add_on: str
    map_method_api_key_plan_basic: str
    map_method_api_key_rate_limit: str
    map_method_api_key_data_gift: str
    map_method_api_key_contract_mobile: str
    map_method_api_key_account_bill: str

    # synonym api config
    synonym_base_url: str = ""
    synonym_api_key: str = ""

    # postgres config
    vector_store_host: str
    vector_store_port: int = 5432
    vector_store_collection_name: str = "map-vector-store"
    vector_store_provider: str = "pgvector"
    vector_store_dbname: str = "map-cypher-vector-store"
    vector_store_user: str
    vector_store_password: str
    vector_store_embedding_model_name: str = "text-embedding-3-small"
    vector_store_embedding_model_dims: int = 1536
    vector_store_diskann: bool = False
    vector_store_hnsw: bool = True

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
