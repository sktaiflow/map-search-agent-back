from dependency_injector import containers, providers

from app.core.tools import ToolExecutor
from app.core.tools.map import MAPToolkitCollectors
from app.core.tools.search import SearchToolkitCollectors
from app.core.tools.search.graph_tool import CypherRunTool
from app.models.vectorstore.semantic_retrieval import SemanticSearchModel
from configs import config as global_config


# 여러 외부 리소스를 조합해 에이전트가 사용할 툴 모음을 제공하는 컨테이너
class ToolkitContainer(containers.DeclarativeContainer):

    clients = providers.DependenciesContainer()
    pgvector_container = providers.DependenciesContainer()
    neo4j_container = providers.DependenciesContainer()

    semantic_model = providers.Object(SemanticSearchModel)
    config_obj = providers.Object(global_config)

    map_tool_collector = providers.Singleton(
        MAPToolkitCollectors,
        map_client=clients.map_api,
    )

    search_tool_collector = providers.Singleton(
        SearchToolkitCollectors,
        llm=clients.openai_chat_llm,
        graph_db=neo4j_container.neo4j_db_engine,
        graphmodel=neo4j_container.neo4j_model,
        postgres_db=pgvector_container.postgres_db,
        vectormodel=semantic_model,
        llm_embedding=clients.embedding_model,
        cfg=config_obj,
    )

    cypher_tool_factory = providers.Factory(
        CypherRunTool,
        llm=clients.openai_chat_llm,
        llm_embedding=clients.embedding_model,
        neo4j_db=neo4j_container.neo4j_db_engine,
        postgres_db=pgvector_container.postgres_db,
        graphmodel=neo4j_container.neo4j_model,
        vectormodel=semantic_model,
        cfg=config_obj,
    )

    tool_collectors = providers.List(map_tool_collector, search_tool_collector)

    tool_executor = providers.Singleton(
        ToolExecutor,
        collectors=tool_collectors,
        extra_tools=providers.List(cypher_tool_factory),
    )

    tools = tool_executor.provided.get_tools.call()
    openai_tools = tool_executor.provided.get_openai_tools.call()
    tool_descriptions = tool_executor.provided.get_tools_description.call()
