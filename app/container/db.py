import asyncio

# python library 모듈
from dependency_injector import containers, providers
from typing import AsyncGenerator
from datetime import timedelta

# app 모듈
from configs import config as global_config
from app import logger

## postgres
from app.database.postgresql import PostgreSQLDatabase
from app.models.vectorstore.base import BaseModel as PGVectorModel
from app.models.vectorstore import list_vector_store_models
from app.models.vectorstore.semantic_retrieval import SemanticSearchModel

## neo4j
from app.models.graphmodel import AsyncGraphModel, GraphModelConfig
from app.database.neo4j import Neo4jDatabase
from neo4j import AsyncGraphDatabase, AsyncDriver, READ_ACCESS, WRITE_ACCESS
from app.models.graphmodel.bootstrap import bootstrap_schema
from app.database.neo4j import Neo4jEngineConfig
from app.container.config import neo4jdriverconfig, graph_model_config, postgresql_engine_config

# Exception
from app.graph.exception import GraphInitError, GraphSchemaEmptyError


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


def _resolve_semantic_search_model(models: list[PGVectorModel] | None) -> SemanticSearchModel:
    models = models or []
    for model in models:
        if isinstance(model, type) and issubclass(model, SemanticSearchModel):
            return model()
    return SemanticSearchModel()


class PGVectorDBContainer(containers.DeclarativeContainer):
    postgres_db = providers.Singleton(
        PostgreSQLDatabase,
        engine_config=postgresql_engine_config,
    )

    pgvector_models = providers.Resource(
        init_pgvector_models,
        postgres_db=postgres_db,
    )

    vectormodel = providers.Singleton(
        lambda models: _resolve_semantic_search_model(models),
        pgvector_models,
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
    # TODO: 프리워밍 코드 필요시 추가 (bootstrap_schema 안쪽에 )
    await bootstrap_schema(driver)
    try:
        yield driver
    finally:
        await driver.close()


async def init_neo4j_graph_cache(
    neo4j_db: Neo4jDatabase,
    model: AsyncGraphModel,
) -> AsyncGenerator[None, None]:
    try:
        async with neo4j_db.get_async_session(mode="r") as session:
            graph_schema = await model._get_schema_str(refresh=True)
            if not graph_schema:
                raise GraphSchemaEmptyError("Graph schema is empty, prewarm failed")
            logger.info(type="graph", message="Graph schema cache prewarmed successfully")
        yield

    # TODO: graph schema cache 실패시에도 앱 서버 뜨게 할거면 코드 변경 필요합니당 (현재는 에러냄)
    except Exception as e:
        logger.error(
            type="graph", message="Failed to prewarm graph schema cache in init", exec_info=e
        )
        raise GraphInitError(f"Failed to prewarm graph schema: {e}") from e


class Neo4jContainer(containers.DeclarativeContainer):

    engine_config = providers.Object(neo4jdriverconfig)

    # Driver는 리소스로 관리 (app life cycle과 수명주기 맞춤)
    neo4j_driver = providers.Resource(
        init_neo4j_driver,
        engine_config=engine_config,
    )

    neo4j_db_engine = providers.Singleton(
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

    graph_model_config = providers.Factory(
        GraphModelConfig,
        cache_schema_ttl=(
            graph_model_config.cache_schema_ttl
            if hasattr(neo4jdriverconfig, "cache_schema_ttl")
            else timedelta(minutes=5)
        ),
        timeout=graph_model_config.timeout if hasattr(neo4jdriverconfig, "timeout") else 1.0,
    )

    neo4j_model = providers.Singleton(
        AsyncGraphModel,
        cfg=graph_model_config,
    )

    # graph schema 생성은 앱 시작시 한번 불러오기
    graph_model_prewarm = providers.Resource(
        init_neo4j_graph_cache,
        neo4j_db=neo4j_db_engine,
        model=neo4j_model,
    )
