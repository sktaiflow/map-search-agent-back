from dependency_injector import containers, providers

from .graphs import GraphContainer
from .agents import AgentContainer

__all__ = ["GraphContainer", "AgentContainer"]


class Container(containers.DeclarativeContainer):
    graphs: GraphContainer = providers.Container(GraphContainer)
    agents: AgentContainer = providers.Container(AgentContainer, graphs=graphs)

    wiring_config = containers.WiringConfiguration(packages=["app"])
