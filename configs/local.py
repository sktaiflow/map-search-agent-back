from configs.default import BaseConfig


class LocalConfig(BaseConfig):
    debug_mode: bool = True
    log_level: str = "INFO"
