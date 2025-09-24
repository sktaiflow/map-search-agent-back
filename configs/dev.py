from configs.default import BaseConfig


class DevConfig(BaseConfig):
    debug_mode: bool = True
    log_level: str = "INFO"

    # MAP API keys (환경별 설정)
    map_method_api_key_plan_add_on: str = ""
    map_method_api_key_plan_basic: str = ""
    map_method_api_key_contract_mobile: str = ""

    # PostgreSQL 설정 (환경별 설정 - AWS Secrets Manager에서 주입)
    postgres_db_host: str = ""
    postgres_db_username: str = ""
    postgres_db_password: str = ""
    vector_store_dbname: str = ""

    # Neo4j 설정 (환경별 설정 - AWS Secrets Manager에서 주입)
    neo4j_nlb_dns: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""
