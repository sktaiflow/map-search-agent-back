import aioboto3

from aioboto3.resources.base import ServiceResource
from aiobotocore.client import BaseClient
from dependency_injector import containers, providers
from typing import AsyncGenerator
from app.database.postgresql import PostgreSQLEngineConfig, PostgreSQLDatabase
from app.models.vectorstore.base import BaseModel as PGVectorModel
from app.models.vectorstore import list_vector_store_models

from configs import config as global_config
from app import logger

postgresql_engine_config = PostgreSQLEngineConfig(
    url=f"postgresql+asyncpg://{global_config.vector_store_user}:{global_config.vector_store_password}@{global_config.vector_store_host}:{global_config.vector_store_port}/{global_config.vector_store_dbname}",
    echo=False,
    pool_size=50,  # 기본 연결 풀 크기 (CPU 코어 수 * 2-4배)
    max_overflow=100,  # 최대 추가 연결 수 (pool_size의 2배)
    pool_timeout=60,  # 연결 대기 시간 (초) - 더 긴 대기 시간
    pool_recycle=3600,  # 연결 재사용 시간 (1시간) - 더 긴 재사용 시간
    pool_pre_ping=True,  # 연결 유효성 검사
)


async def init_pgvector_models(
    postgres_db: PostgreSQLDatabase,
) -> AsyncGenerator[list[PGVectorModel], None]:
    models = list_vector_store_models()
    logger.info(f"Initializing PGVector models: {[model.__tablename__ for model in models]}")
    engine = postgres_db.engine
    try:
        for model in models:
            await model.create_table_and_hnsw_index(engine=engine)
        yield models
    except Exception as e:
        logger.error(f"Error initializing PGVector models: {e}")
        yield e


class PGVectorDBContainer(containers.DeclarativeContainer):
    postgres_db = providers.Singleton(
        PostgreSQLDatabase,
        engine_config=postgresql_engine_config,
    )

    pgvector_models = providers.Resource(
        init_pgvector_models,
        postgres_db=postgres_db,
    )


from neo4j import AsyncGraphDatabase, READ_ACCESS, WRITE_ACCESS


class Neo4jContainer(containers.DeclarativeContainer):

    driver = providers.Singleton(
        AsyncGraphDatabase.driver,
        uri=f"{global_config.neo4j_nlb_dns}:{global_config.neo4j_bolt_port}",
        auth=providers.Callable(
            lambda u, p: (u, p), global_config.neo4j_username, global_config.neo4j_password
        ),
        max_connection_lifetime=60,
        max_connection_pool_size=50,
    )

    session = providers.Resource(lambda d: _neo4j_session(d), driver)


async def _neo4j_session(driver):
    async with driver.session(default_access_mode=READ_ACCESS) as session:
        yield session
