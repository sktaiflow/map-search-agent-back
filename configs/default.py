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

    stack_type: StackType = os.environ.get("STACK_TYPE", StackType.LOCAL)

    model_config = SettingsConfigDict(
        env_file=f".env.{stack_type}",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = os.environ.get("APP_NAME", "map-search-agent")
    api_version: str = os.getenv("API_VERSION", "0.0.1")

    # smart bee
    openai_api_base: str = ""
    openai_api_key: str = ""
    aws_region: str = "ap-northeast-2"
    neo4j_connection_config: dict[str, Any] = {
        "neo4j_nlb_dns": "",
        "nlb_port": 7687,
        "neo4j_username": "",
        "neo4j_password": "",
    }
