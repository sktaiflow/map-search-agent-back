from dependency_injector import containers, providers
from langgraph.checkpoint.memory import MemorySaver
from app.core.graph import MapSearchGraph


class GraphContainer(containers.DeclarativeContainer):
    # Graph 인스턴스를 싱글톤으로 관리
    memory_saver = providers.Factory(MemorySaver)
    map_search_graph = providers.Singleton(
        MapSearchGraph,
        checkpointer=memory_saver,
    )
