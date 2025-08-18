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


class MAPAPIError(ExternalRequestError):
    def __init__(
        self,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        message: Optional[str] = None,
    ):
        super().__init__("UPS API", status_code, code=code, message=message)
        self.code = code
        self.message = message


class MAPClient:
    def __init__(self, http_client: HTTPBaseClient, host: str, api_key: str):
        self._http_client = http_client
        self._host = host
        self._api_key = api_key

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, traceback):
        await self._http_client.__aexit__(exc_type, exc_val, traceback)

    async def close(self):
        await self._http_client.close()

    @traced
    async def _request(
        self, method: str, endpoint: str, headers: dict[str, Any] = {}, **kwargs
    ) -> HTTPBaseClientResponse:
        try:
            url = f"{self._host}{endpoint}"
            ## 헤더 API KEY 추가
            headers = {"x-apim-key": self._api_key, "content-type": "application/json", **headers}
            # logger.info(type="map-request", url=url, method=method, extra=kwargs)
            response = await self._http_client.request(method, url, headers=headers, **kwargs)
            if response.status != 200:
                raise InvalidHttpStatus(response.status, response.body)

            return response

        except InvalidHttpStatus as e:
            try:
                data = json.loads(e.body)
                code, message = data.get("code"), data.get("message")
            except Exception:
                code, message = None, None
                raise MAPAPIError(e.status, code, message)
        except Exception as e:
            raise MAPAPIError(message=str(e))
