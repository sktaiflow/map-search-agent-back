from typing import Dict, Any, Optional
from app.clients.http_base import HTTPBaseClient, InvalidHttpStatus, HTTPBaseClientResponse
from utils.trace import traced, trace
from utils import logger
import json


class ExternalRequestError(Exception):
    def __init__(self, api: str, status_code: Optional[int] = None, **details) -> None:
        ctx = ", ".join([f"{k}={v}" for k, v in {"status_code": status_code, **details}.items()])
        super().__init__(f"Fail to request {api} ({ctx})")
        self.api = api
        self.status_code = status_code


class SynonymAPIError(ExternalRequestError):
    def __init__(
        self,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        message: Optional[str] = None,
    ):
        super().__init__("UPS API", status_code, code=code, message=message)
        self.code = code
        self.message = message


# TODO: 동의어 API 나오면 구현
class SynonymClient:
    def __init__(self, http_client: HTTPBaseClient, host: str, api_key: str):
        self._http_client = http_client
        self._host = host
        self._api_key = api_key

    async def _request(self, method: str, endpoint: str, headers: dict[str, Any] = {}, **kwargs):
        pass
