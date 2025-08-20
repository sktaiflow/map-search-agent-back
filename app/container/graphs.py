from dependency_injector import containers, providers
from langgraph.checkpoint.memory import MemorySaver
from core.graph.map_search_graph import MapSearchGraph
from configs import config as global_config


class GraphContainer(containers.DeclarativeContainer):
    # Graph 인스턴스를 싱글톤으로 관리
    memory_saver = providers.Factory(MemorySaver)
    map_search_graph = providers.Singleton(
        MapSearchGraph,
        checkpointer=memory_saver,
    )
