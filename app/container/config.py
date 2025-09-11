from configs import config as global_config

from app.database.neo4j import Neo4jEngineConfig
from app.database.postgresql import PostgreSQLEngineConfig
from app.models.graphmodel import GraphModelConfig
from datetime import timedelta

## db config

neo4jdriverconfig = Neo4jEngineConfig(
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

graph_model_config = GraphModelConfig(
    cache_schema_ttl=timedelta(minutes=5),
    timeout=1.0,
)

postgresql_engine_config = PostgreSQLEngineConfig(
    url=f"postgresql+asyncpg://{global_config.postgres_db_username}:{global_config.postgres_db_password}@{global_config.postgres_db_host}:{global_config.postgres_db_port}/{global_config.vector_store_dbname}",
    echo=False,
    pool_size=50,  # 기본 연결 풀 크기 (CPU 코어 수 * 2-4배)
    max_overflow=100,  # 최대 추가 연결 수 (pool_size의 2배)
    pool_timeout=60,  # 연결 대기 시간 (초) - 더 긴 대기 시간
    pool_recycle=3600,  # 연결 재사용 시간 (1시간) - 더 긴 재사용 시간
    pool_pre_ping=True,  # 연결 유효성 검사
)
