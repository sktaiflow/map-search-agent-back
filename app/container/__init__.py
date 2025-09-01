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
    clients = providers.Container(ClientContainer, neo4j_db=neo4j_db)
    llm = providers.Container(LLMContainer)
    toolkit = providers.Container(ToolkitContainer, clients=clients)
    graphs = providers.Container(
        GraphContainer,
        client_container=clients,
        neo4j_container=neo4j_db,
        toolkit_container=toolkit,
        pgvector_container=pgvector_db,
    )
    agents = providers.Container(AgentContainer, graphs=graphs, http_client=clients)
    wiring_config = containers.WiringConfiguration(packages=["app"])
    
    async def init_resources(self):
        """Initialize database connections"""
        try:
            # Initialize the same Neo4j database instance used across all containers
            neo4j_instance = self.neo4j_db.neo4j_db()
            await neo4j_instance.connect()
            print("Neo4j database connected successfully")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def shutdown_resources(self):
        """Cleanup database connections"""
        await self.neo4j_db.neo4j_db().close()
