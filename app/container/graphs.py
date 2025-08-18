from dependency_injector import containers, providers
from langgraph.checkpoint.memory import MemorySaver
from app.graphs import MapProductGraph


class GraphContainer(containers.DeclarativeContainer):
    # Graph 인스턴스를 싱글톤으로 관리
    memory_saver = providers.Factory(MemorySaver)
    schedule_graph = providers.Singleton(
        MapProductGraph,
        checkpointer=memory_saver,
    )
