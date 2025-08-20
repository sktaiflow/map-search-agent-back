from typing import Optional


class ExternalRequestError(Exception):
    def __init__(self, api: str, status_code: Optional[int] = None, **details) -> None:
        ctx = ", ".join([f"{k}={v}" for k, v in {"status_code": status_code, **details}.items()])
        super().__init__(f"Fail to request {api} ({ctx})")
        self.api = api
        self.status_code = status_code
