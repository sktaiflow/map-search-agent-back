from dependency_injector import containers, providers

from .graphs import GraphContainer
from .agents import AgentContainer
from .db import PGVectorDBContainer
from .clients import ClientContainer

__all__ = ["GraphContainer", "AgentContainer", "PGVectorDBContainer", "ClientContainer"]


class Container(containers.DeclarativeContainer):
    # graphs: GraphContainer = providers.Container(GraphContainer)
    # agents: AgentContainer = providers.Container(AgentContainer, graphs=graphs)
    pgvector_db: PGVectorDBContainer = providers.Container(PGVectorDBContainer)
    clients: ClientContainer = providers.Container(ClientContainer)
    wiring_config = containers.WiringConfiguration(packages=["app"])
