from typing import Dict, Any, Optional
from .http_base import HTTPBaseClient


class MAPClient:
    def __init__(self, http_client: HTTPBaseClient, host: str):
        self._http_client = http_client
        self._host = host

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, traceback):
        await self._http_client.__aexit__(exc_type, exc_val, traceback)

    async def close(self):
        await self.http_client.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """HTTP 요청 실행"""
        url = f"{self.base_url}/{endpoint}"
        # 헤더에 API 키 추가
        headers = kwargs.get("headers", {})
        headers.update({"x-apim-key": self.api_key})
        kwargs["headers"] = headers

        async with self.http_client as client:
            try:
                response = await client.request(method, url, **kwargs)

                # HTTP 상태 코드 확인
                if response.status >= 400:
                    raise Exception(f"HTTP {response.status}: {response.text()}")

                # JSON 응답 반환
                return response.json()

            except Exception as e:
                print(f"MAP API 요청 실패: {method} {url}")
                print(f"에러: {e}")
                raise
