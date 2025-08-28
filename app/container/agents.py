from dependency_injector import containers, providers
from app.clients.http_base import HTTPBaseClient
from app.models.vectorstore.base import BaseModel as PGVectorModel

from app.agents.map_search_agent import MapSearchAgent
from app.container import GraphContainer


# TODO: synonyhm api 호출을 graph에서 할거면 추후 제거 필요
class AgentContainer(containers.DeclarativeContainer):
    ## http client, graph 주입
    graphs = providers.DependenciesContainer()
    http_client = providers.DependenciesContainer()

    map_agent = providers.Singleton(
        MapSearchAgent,
        graph=graphs.map_search_graph,
        http_client=http_client.synonym_api,
    )

    factory = providers.Dict(
        {
            MapSearchAgent.config.agent_name: map_agent,
        }
    )
