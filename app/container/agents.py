from dependency_injector import containers, providers
from app.clients.http_base import HTTPBaseClient
from app.models.vectorstore.base import BaseModel as PGVectorModel

from app.agents import MapSearchAgent
from app.container import GraphContainer


class AgentContainer(containers.DeclarativeContainer):
    graphs: GraphContainer = providers.DependenciesContainer()
    http_client: HTTPBaseClient = providers.DependenciesContainer()
    pgvector_models: list[PGVectorModel] = providers.DependenciesContainer()

    map_agent = providers.Singleton(
        MapSearchAgent,
        graph=graphs.map_agent,
    )

    factory = providers.Dict(
        {
            MapSearchAgent.config.agent_name: map_agent,
        }
    )
