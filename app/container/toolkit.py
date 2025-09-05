from dependency_injector import containers, providers

from app.core.tools.map import MAPToolkitCollectors
from app.core.tools.search import SearchToolkitCollectors
from app.core.tools import create_agent_tools_data
from configs import config as global_config


class ToolkitContainer(containers.DeclarativeContainer):
    """최적화된 툴킷 컨테이너 - 함수 기반, 개별 컬렉터 내부화"""

    clients = providers.DependenciesContainer()
    db = providers.DependenciesContainer()

    _agent_tools_data = providers.Singleton(
        create_agent_tools_data,
        tool_collectors=providers.List(
            providers.Singleton(
                MAPToolkitCollectors,
                map_client=clients.map_api,
                method_api_key=global_config.map_method_api_keys,
            ),
            providers.Singleton(
                SearchToolkitCollectors,
                llm=clients.openai_chat_llm,
                graph_db=db.neo4j_db,
                graphmodel=db.neo4j_model,
            ),
        ),
    )
