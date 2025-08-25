import os
import boto3
from dotenv import load_dotenv


from configs.default import BaseConfig, StackType
import utils.json as json

DEFAULT_SECRET_ID = "map_secrete"


def get_config(stack_type: str) -> BaseConfig:
    if stack_type == StackType.LOCAL:
        from configs.local import LocalConfig

        from pathlib import Path

        env_file = Path(__file__).parent / f".env.local"
        if not env_file.exists():
            raise FileNotFoundError(f"env file not found: {env_file}")
        load_dotenv(dotenv_path=env_file)
        return LocalConfig(_env_file=str(env_file), _env_file_encoding="utf-8")

    secrets_manager = boto3.client("secretsmanager")

    response = secrets_manager.get_secret_value(SecretId=DEFAULT_SECRET_ID)
    secret = json.loads(response["SecretString"])

    # 환경 변수 설정
    for key, value in secret.items():
        os.environ[key] = str(value)

    if stack_type == StackType.DEV:
        from configs.dev import DevConfig

        return DevConfig(**secret)

    elif stack_type == StackType.STG:
        from configs.stg import StgConfig

        return StgConfig(**secret)

    elif stack_type == StackType.PRD:
        from configs.prd import PrdConfig

        return PrdConfig(**secret)
    else:
        raise Exception(f"Invalid stack type: {stack_type}")


PHASE = os.environ.get("STACK_TYPE", StackType.LOCAL)

config: BaseConfig = get_config(PHASE)

__all__ = ["config", "StackType"]
