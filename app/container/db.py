import asyncio

from dependency_injector import containers, providers
from typing import AsyncGenerator

from configs import config as global_config
from app import logger

## postgres
from app.database.postgresql import PostgreSQLEngineConfig, PostgreSQLDatabase
from app.models.vectorstore.base import BaseModel as PGVectorModel
from app.models.vectorstore import list_vector_store_models

## neo4j
from app.database.neo4j import Neo4jDatabase
from app.models.graphmodel.base import BaseGraphModel
from neo4j import AsyncGraphDatabase, AsyncDriver, READ_ACCESS, WRITE_ACCESS
from app.models.graphmodel.bootstrap import bootstrap_schema
from app.database.neo4j import Neo4jEngineConfig
from typing import Type

postgresql_engine_config = PostgreSQLEngineConfig(
    url=f"postgresql+asyncpg://{global_config.postgres_db_username}:{global_config.postgres_db_password}@{global_config.postgres_db_host}:{global_config.postgres_db_port}/{global_config.vector_store_dbname}",
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
            # await model.drop_table(engine=engine) # Test용 코드 (테이블삭제), stg, prd에서는 사용 X
            await model.create_table_and_hnsw_index(engine=engine)
        yield models
    except Exception as e:
        logger.error(message=f"Error initializing PGVector models", exec_info=e)
        raise


class PGVectorDBContainer(containers.DeclarativeContainer):
    postgres_db = providers.Singleton(
        PostgreSQLDatabase,
        engine_config=postgresql_engine_config,
    )

    pgvector_models = providers.Resource(
        init_pgvector_models,
        postgres_db=postgres_db,
    )


neo4jclientconfig = Neo4jEngineConfig(
    uri=f"{global_config.neo4j_nlb_dns}:{global_config.neo4j_bolt_port}",
    user=global_config.neo4j_username,
    password=global_config.neo4j_password,
    max_concurrent_sessions=70,
    max_connection_pool_size=100,
    connection_timeout=1.0,
    keep_alive=True,
    liveness_check_timeout=5.0,
    connection_acquisition_timeout=1.0,
    max_transaction_retry_time=5.0,
    max_connection_lifetime=1800,
    initial_retry_delay=0.5,
    retry_delay_multiplier=2.0,
    retry_delay_jitter_factor=0.3,
)


async def init_neo4j_driver(engine_config: Neo4jEngineConfig) -> AsyncGenerator[AsyncDriver, None]:
    def _ensure_scheme(uri: str) -> str:
        if uri.startswith(("neo4j://", "neo4j+s://", "bolt://", "bolt+s://")):
            return uri

        return f"bolt://{uri}"

    uri = _ensure_scheme(engine_config.uri)
    pool_size = getattr(
        engine_config, "max_connection_pool_size", getattr(engine_config, "max_pool_size", 50)
    )

    driver = AsyncGraphDatabase.driver(
        uri,
        auth=(engine_config.user, engine_config.password),
        max_connection_pool_size=pool_size,
        connection_timeout=engine_config.connection_timeout,
        keep_alive=engine_config.keep_alive,
        liveness_check_timeout=engine_config.liveness_check_timeout,
        connection_acquisition_timeout=engine_config.connection_acquisition_timeout,
        max_transaction_retry_time=engine_config.max_transaction_retry_time,
        max_connection_lifetime=engine_config.max_connection_lifetime,
        initial_retry_delay=engine_config.initial_retry_delay,
        retry_delay_multiplier=engine_config.retry_delay_multiplier,
        retry_delay_jitter_factor=engine_config.retry_delay_jitter_factor,
    )

    await driver.verify_connectivity()
    await bootstrap_schema(driver)
    try:
        yield driver
    finally:
        await driver.close()


# TODO: BaseGraphModel 대신 CypherAgent 구현체로 바꿔야함
class Neo4jContainer(containers.DeclarativeContainer):

    engine_config = providers.Object(neo4jclientconfig)

    # Driver는 리소스로 관리 (app life cycle과 수명주기 맞춤)
    neo4j_driver = providers.Resource(
        init_neo4j_driver,
        engine_config=engine_config,
    )

    neo4j_db = providers.Singleton(
        Neo4jDatabase,
        driver=neo4j_driver,
        engine_config=engine_config,
        max_concurrent_sessions=providers.Callable(
            lambda cfg: getattr(cfg, "max_concurrent_sessions", None), engine_config
        ),
        default_database=providers.Callable(
            lambda cfg: getattr(cfg, "database", "neo4j"), engine_config
        ),
    )

    neo4j_model = providers.Singleton(BaseGraphModel)
