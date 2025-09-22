from dependency_injector import containers, providers

from .graphs import GraphContainer
from .agents import AgentContainer
from .db import PGVectorDBContainer, Neo4jContainer
from .clients import ClientContainer
from .toolkit import ToolkitContainer

__all__ = [
    "GraphContainer",
    "AgentContainer",
    "PGVectorDBContainer",
    "Neo4jContainer",
    "ClientContainer",
    "ToolkitContainer",
]


class Container(containers.DeclarativeContainer):
    pgvector_db = providers.Container(PGVectorDBContainer)
    neo4j_db = providers.Container(Neo4jContainer)
    clients = providers.Container(ClientContainer)
    toolkit = providers.Container(
        ToolkitContainer,
        clients=clients,
        pgvector_container=pgvector_db,
        neo4j_container=neo4j_db,
    )
    graphs = providers.Container(
        GraphContainer,
        client_container=clients,
        toolkit_container=toolkit,
        pgvector_container=pgvector_db,
        neo4j_container=neo4j_db,
    )
    agents = providers.Container(AgentContainer, graphs=graphs, http_client=clients)
    wiring_config = containers.WiringConfiguration(packages=["app"])
