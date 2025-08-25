from dependency_injector import containers, providers
from langgraph.checkpoint.memory import MemorySaver
from app.container.db import Neo4jContainer
from app.container.llm import LLMContainer
from configs import config as global_config
from app.graph.schema import Deps
from app.graph.map_search_graph import MapSearchGraph


class GraphContainer(containers.DeclarativeContainer):
    # Graph 인스턴스를 싱글톤으로 관리 -> Graph에서는 node에서 사용하는 llm, neo4j, tools주입.
    # llm_container = providers.DependenciesContainer()
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
        toolkit=toolkit_container.map_toolkit,
        tools=toolkit_container.map_tools,
    )

    memory_saver = providers.Factory(MemorySaver)
    map_search_graph = providers.Singleton(
        MapSearchGraph,
        checkpointer=memory_saver,
        deps=deps,
    )
