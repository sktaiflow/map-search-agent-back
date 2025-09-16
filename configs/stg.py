from configs.default import BaseConfig


class StgConfig(BaseConfig):
    debug_mode: bool = False
    log_level: str = "INFO"
    
    # MAP API keys (환경별 설정)
    map_method_api_key_plan_add_on: str = ""
    map_method_api_key_plan_basic: str = ""
    map_method_api_key_contract_mobile: str = ""
