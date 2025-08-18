from typing import Dict, Any, Optional
from app.clients.http_base import HTTPBaseClient, InvalidHttpStatus
from utils.trace import traced, trace
from utils import logger
import json


class MAPClient:
    def __init__(self, http_client: HTTPBaseClient, host: str, api_key: str):
        self._http_client = http_client
        self._host = host.rstrip("/")
        self._api_key = api_key

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, traceback):
        await self._http_client.__aexit__(exc_type, exc_val, traceback)

    async def close(self):
        await self._http_client.close()

    @traced
    async def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """HTTP 요청 실행"""
        try:
            url = f"{self._host}/{endpoint.lstrip('/')}"
            ## 헤더 API KEY 추가
            headers = {"x-apim-key": self._api_key}
            logger.info(type="map-request", url=url, method=method, extra=kwargs)
            response = await self._http_client.request(method, url, headers=headers, **kwargs)
            if response.status != 200:
                raise InvalidHttpStatus(response.status, response.body)
            try:
                response_data = response.json()
            except Exception as e:
                response_data = response.text()

            logger.info(type="map_response", response=response_data)
            return response.json()
        except InvalidHttpStatus as e:
            print(f"MAP API 요청 실패: {method} {url}")
            print(f"에러: {e}")
            raise

        except Exception as e:
            print(">>>>> Exception in MapAPIClient._request, ", e)
            raise
