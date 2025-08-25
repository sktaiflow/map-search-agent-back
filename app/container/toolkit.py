from dependency_injector import containers, providers

from app.core.tools.map import (
    ContractToolKit,
    PlanToolKit,
    MAPTools,
)

from configs import config as global_config


# TODO meta 검색 툴 [cypher agent] 추가 주입 필요
class ToolkitContainer(containers.DeclarativeContainer):
    clients = providers.DependenciesContainer()

    map_toolkit = providers.Factory(
        MAPTools,
        map_client=clients.map_api,
        method_api_key=global_config.map_method_api_keys,
    )

    map_tools = providers.Factory(
        lambda toolkit: toolkit.get_valid_tools(),
        toolkit=map_toolkit,
    )
