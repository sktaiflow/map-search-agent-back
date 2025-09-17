from dependency_injector import containers, providers
from langgraph.checkpoint.memory import MemorySaver
from app.graph.schema import Deps
from app.graph.map_search_graph import MapSearchGraph
from configs import config as global_config


# TODO: tool 기능이 명확화되면 -> graph에서 빠져야할 것들 빠져야함, memory saver 넣을지 말지 필요
class GraphContainer(containers.DeclarativeContainer):
    client_container = providers.DependenciesContainer()
    neo4j_container = providers.DependenciesContainer()
    toolkit_container = providers.DependenciesContainer()
    pgvector_container = providers.DependenciesContainer()

    deps = providers.Factory(
        Deps,
        llm_client=client_container.openai_chat_llm,
        embed_client=client_container.embedding_model,
        postgres_db=pgvector_container.postgres_db,
        pgvector_models=pgvector_container.pgvector_models,
        # TODO: 그냥 neo4j_container가 가는게 맞는건지 .neo4j_db_engine가 가는게 맞는건지 확인 필요
        neo4j_client=neo4j_container.neo4j_db_engine,
        # TODO: 아래 둘의 차이가 뭐지..? 아래껀 원래 openai_tools 였음
        toolkit=toolkit_container.tool_executor,
        tools=toolkit_container.tools,
    )

    memory_saver = providers.Factory(MemorySaver)
    map_search_graph = providers.Singleton(
        MapSearchGraph,
        checkpointer=memory_saver,
        deps=deps,
    )
