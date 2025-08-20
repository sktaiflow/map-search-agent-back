from dependency_injector import containers, providers

from app.agents.map_search_agent import MapSearchAgent
from app.container.graphs import GraphContainer


class AgentContainer(containers.DeclarativeContainer):
    graphs: GraphContainer = providers.DependenciesContainer()

    map_search_agent = providers.Singleton(
        MapSearchAgent,
        graph=graphs.map_search_graph,
    )

    factory = providers.Dict(
        {
            MapSearchAgent.config.agent_name: map_search_agent,
        }
    )
