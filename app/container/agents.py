from dependency_injector import containers, providers

from app.agents.schedule_agent_with_graph import 
from app.core.containers import GraphContainer


class AgentContainer(containers.DeclarativeContainer):
    graphs: GraphContainer = providers.DependenciesContainer()

    map_agent = providers.Singleton(
        MAPSearchAgent,
        graph=graphs.map_agent,
    )

    factory = providers.Dict(
        {
            MAPSearchAgent.config.agent_name: map_agent,
        }
    )
