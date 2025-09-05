from configs.default import BaseConfig


class DevConfig(BaseConfig):
    debug_mode: bool = True
    log_level: str = "INFO"
