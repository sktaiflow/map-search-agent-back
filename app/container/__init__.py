from dependency_injector import containers, providers

from .graphs import GraphContainer
from .agents import AgentContainer
from .db import PGVectorDBContainer
from .clients import ClientContainer
from .llm import LLMContainer
from .toolkit import ToolkitContainer

__all__ = [
    "GraphContainer",
    "AgentContainer",
    "PGVectorDBContainer",
    "ClientContainer",
    "LLMContainer",
    "ToolkitContainer",
]


class Container(containers.DeclarativeContainer):
    graphs: GraphContainer = providers.Container(GraphContainer)
    pgvector_db: PGVectorDBContainer = providers.Container(PGVectorDBContainer)
    clients: ClientContainer = providers.Container(ClientContainer)
    agents: AgentContainer = providers.Container(AgentContainer, graphs=graphs)
    llm: LLMContainer = providers.Container(LLMContainer)
    toolkit: ToolkitContainer = providers.Container(ToolkitContainer)
    wiring_config = containers.WiringConfiguration(packages=["app"])
