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
        neo4j_client=neo4j_container,
        toolkit=toolkit_container.tool_executor,
        tools=toolkit_container.openai_tools,
    )

    memory_saver = providers.Factory(MemorySaver)
    map_search_graph = providers.Singleton(
        MapSearchGraph,
        checkpointer=memory_saver,
        deps=deps,
    )
