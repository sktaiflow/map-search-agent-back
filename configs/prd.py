from configs.default import BaseConfig


class PrdConfig(BaseConfig):
    debug_mode: bool = False
    log_level: str = "ERROR"
