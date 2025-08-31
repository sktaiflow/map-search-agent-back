from dependency_injector import containers, providers

from app.core.tools.map import (
    ContractToolKit,
    PlanToolKit,
    MAPTools,
)
from app.core.tools.neo4j import Neo4jToolKit

from configs import config as global_config


class ToolkitContainer(containers.DeclarativeContainer):
    clients = providers.DependenciesContainer()

    neo4j_toolkit = providers.Factory(
        Neo4jToolKit,
        cypher_qa_chain=clients.neo4j_cypher_qa_chain,
    )

    map_toolkit = providers.Factory(
        MAPTools,
        map_client=clients.map_api,
        method_api_key=global_config.map_method_api_keys,
        neo4j_toolkit=neo4j_toolkit,
    )

    map_tools = providers.Factory(
        lambda toolkit: toolkit.get_valid_tools(),
        toolkit=map_toolkit,
    )
    
    neo4j_tools = providers.Factory(
        lambda toolkit: toolkit.get_valid_tools(),
        toolkit=neo4j_toolkit,
    )
