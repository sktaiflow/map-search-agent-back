from dependency_injector import containers, providers

from app.core.tools.map_api_tools import (
    CheckPlanEligibilityTool,
    GetContractServicesTool,
    GetPlanSubscriptionsTool,
)
from app.core.tools.neo4j_search_tool import Neo4jSearchTool
from configs import config as global_config


class ToolkitContainer(containers.DeclarativeContainer):

    clients = providers.DependenciesContainer()
    pgvector_container = providers.DependenciesContainer()
    neo4j_container = providers.DependenciesContainer()

    # MAP API 툴들 - 각각 올바른 method_api_key 주입
    get_contract_services_tool = providers.Singleton(
        GetContractServicesTool,
        map_client=clients.map_api,
        method_api_key=global_config.map_api_method_key_contract_mobile,
    )

    get_plan_subscriptions_tool = providers.Singleton(
        GetPlanSubscriptionsTool,
        map_client=clients.map_api,
        method_api_key=global_config.map_api_method_key_plan_add_on,
    )

    check_plan_eligibility_tool = providers.Singleton(
        CheckPlanEligibilityTool,
        map_client=clients.map_api,
        method_api_key=global_config.map_api_method_key_plan_basic,
    )

    # Neo4j Search 툴
    neo4j_search_tool = providers.Singleton(
        Neo4jSearchTool,
        llm=clients.openai_chat_llm,
        llm_embedding=clients.embedding_model,
        neo4j_db=neo4j_container.neo4j_db_engine,
        postgres_db=pgvector_container.postgres_db,
        graphmodel=neo4j_container.neo4j_model,
        vectormodel=pgvector_container.vectormodel,
        cfg=global_config,
    )

    # 활성화된 모든 툴들 (status=True인 것만)
    all_active_tools = providers.List(
        get_contract_services_tool,
        get_plan_subscriptions_tool,
        check_plan_eligibility_tool,
        neo4j_search_tool,
    )
