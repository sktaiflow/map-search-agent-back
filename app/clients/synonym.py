from typing import Dict, Any, Optional
from app.clients.http_base import HTTPBaseClient, InvalidHttpStatus, HTTPBaseClientResponse
from app import logger
import utils.json as json


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
        super().__init__("Synonym API", status_code, code=code, message=message)
        self.code = code
        self.message = message


# TODO: 동의어 API 나오면 구현
class SynonymClient:
    def __init__(self, http_client: HTTPBaseClient, host: str, api_key: str):
        self._http_client = http_client
        self._host = host
        self._api_key = api_key

    async def _request(
        self, method: str, endpoint: str, headers: dict[str, Any] = {}, **kwargs
    ) -> HTTPBaseClientResponse:
        try:
            url = f"{self._host}{endpoint}"
            ## 헤더 API KEY 추가
            headers = {"x-apim-key": self._api_key, "content-type": "application/json", **headers}
            logger.info(type="synonym-request", url=url, method=method, extra=kwargs)
            response = await self._http_client.request(method, url, headers=headers, **kwargs)
            if response.status != 200:
                raise InvalidHttpStatus(response.status, response.body)

            response_data = response.json()

            logger.info(type="synonym-response", response=response_data)
            if response.status // 100 != 2:
                raise InvalidHttpStatus(response.status, response.body)

            return response

        except InvalidHttpStatus as e:
            try:
                data = json.loads(e.body)
                code, message = data.get("code"), data.get("message")
            except Exception:
                code, message = None, None
                raise SynonymAPIError(e.status, code, message)
        except Exception as e:
            raise SynonymAPIError(message=str(e))
