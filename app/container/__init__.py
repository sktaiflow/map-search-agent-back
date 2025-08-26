from dependency_injector import containers, providers

from .graphs import GraphContainer
from .agents import AgentContainer
from .db import PGVectorDBContainer, Neo4jContainer
from .clients import ClientContainer
from .llm import LLMContainer
from .toolkit import ToolkitContainer

__all__ = [
    "GraphContainer",
    "AgentContainer",
    "PGVectorDBContainer",
    "Neo4jContainer",
    "ClientContainer",
    "LLMContainer",
    "ToolkitContainer",
]


class Container(containers.DeclarativeContainer):
    pgvector_db = providers.Container(PGVectorDBContainer)
    neo4j_db = providers.Container(Neo4jContainer)
    clients = providers.Container(ClientContainer)
    llm = providers.Container(LLMContainer)
    toolkit = providers.Container(ToolkitContainer, clients=clients)
    graphs = providers.Container(
        GraphContainer,
        client_container=clients,
        neo4j_container=neo4j_db,
        toolkit_container=toolkit,
        pgvector_container=pgvector_db,
    )
    agents = providers.Container(
        AgentContainer, graphs=graphs, http_client=clients, pgvector_models=pgvector_db
    )
    wiring_config = containers.WiringConfiguration(packages=["app"])
