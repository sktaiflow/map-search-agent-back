from dependency_injector import containers, providers

from app.core.tools.map import (
    GetContractMobileContractDevicesTool,
    GetPlanAddOnAddOnSubscriptionsTool,
)

from configs import config as global_config


class ToolkitContainer(containers.DeclarativeContainer):
    clients = providers.DependenciesContainer()

    get_contract_mobile_contract_devices = providers.Factory(
        GetContractMobileContractDevicesTool,
        map_client=clients.map_api,
        method_api_key=global_config.map_method_api_key_contract_mobile_device,
    )
    get_plan_add_on_add_on_subscriptions = providers.Factory(
        GetPlanAddOnAddOnSubscriptionsTool,
        map_client=clients.map_api,
        method_api_key=global_config.map_method_api_key_plan_add_on,
    )
