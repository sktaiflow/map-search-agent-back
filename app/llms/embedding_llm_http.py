from typing import Optional

from app.clients.http_base import HTTPBaseClient, InvalidHttpStatus
from app.errors import ExternalRequestError
import json


class SmartbeeEmbeddingAPIError(ExternalRequestError):
    def __init__(
        self,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        message: Optional[str] = None,
    ):
        super().__init__("PE Tool Embedding API", status_code, code=code, message=message)
        self.code = code
        self.message = message


class SmartbeeEmbeddingModel:
    def __init__(
        self,
        http_client: HTTPBaseClient,
        host: str,
        api_key: str,
        model: str = "text-embedding-3-small",
    ):
        self._http_client = http_client
        self._host = host
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str = None, texts: list[str] = None):
        if text:
            request_data = {
                "service_code": "map-search-agent",
                "input": text.replace("\n", " "),
                "model": self._model,
                "encoding_format": "float",
            }
        elif texts:
            request_data = {
                "service_code": "map-search-agent",
                "input": [text.replace("\n", " ") for text in texts],
                "model": self._model,
                "encoding_format": "float",
            }
        else:
            raise ValueError("Either text or texts must be provided")

        headers = {
            "content-type": "application/json",
        }

        try:
            response = await self._http_client.request(
                method="POST",
                url=f"{self._host}/api/v1/embeddings",
                headers=headers,
                json=request_data,
            )
            if response.status // 100 != 2:
                raise InvalidHttpStatus(response.status, response.body)

            return response.json()["res"]["data"][0]["embedding"]
        except InvalidHttpStatus as e:
            try:
                data = json.loads(e.body)
                code, message = data.get("state"), data.get("res", {}).get("error", {}).get(
                    "message"
                )
            except Exception:
                code, message = None, None
            raise SmartbeeEmbeddingAPIError(e.status, code, message)
        except Exception as e:
            raise SmartbeeEmbeddingAPIError(message=str(e))
