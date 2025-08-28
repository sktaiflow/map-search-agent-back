from typing import Optional, List

from app.clients.http_base import HTTPBaseClient, InvalidHttpStatus
from app.errors import ExternalRequestError
import utils.json as json
from pydantic import BaseModel


class LLMEmbeddingAPIError(ExternalRequestError):
    def __init__(
        self,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        message: Optional[str] = None,
    ):
        super().__init__("OpenAI Embedding API", status_code, code=code, message=message)
        self.code = code
        self.message = message


class EmbeddingUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingData(BaseModel):
    object: str
    index: int
    embedding: List[float]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    prompt_tokens: int
    total_tokens: int


class OpenAIEmbeddingModel:
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

    async def aembed_petool(self, text: str, texts: list[str]):
        if text:
            request_data = {
                "service_code": "",  # TODO: Smartbee에서는 필요없음
                "input": text.replace("\n", " "),
                "model": self._model,
                "encoding_format": "float",
            }

        elif texts:
            request_data = {
                "service_code": "",  # TODO: Smartbee에서는 필요없음
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
                url=f"{self._host}/embeddings",
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
            raise LLMEmbeddingAPIError(e.status, code, message)
        except Exception as e:
            raise LLMEmbeddingAPIError(message=str(e))

    async def aembed(
        self, text: str = None, texts: list[str] = None, model: str = "text-embedding-3-small"
    ):
        """smartbee embedding api 호출"""
        if not (text is not None) ^ (texts is not None):
            raise ValueError("Either text or texts must be provided")

        request_data = {"input": text if text is not None else texts, "model": model}
        headers = {
            "content-type": "application/json",
            "Authorization": f"{self._api_key}",
        }
        try:
            response = await self._http_client.request(
                method="POST",
                url=f"{self._host}/embeddings",
                headers=headers,
                json=request_data,
            )
            if response.status // 100 != 2:
                raise InvalidHttpStatus(response.status, response.body)

            response_data = response.json()
            embeddings = []
            for item in response_data["data"]:
                embeddings.append(item["embedding"])

            return EmbeddingResponse(
                **{
                    "embeddings": embeddings,
                    "model": response_data["model"],
                    "prompt_tokens": response_data["usage"]["prompt_tokens"],
                    "total_tokens": response_data["usage"]["total_tokens"],
                }
            )

        except InvalidHttpStatus as e:
            try:
                data = json.loads(e.body)
                code, message = data.get("state"), data.get("res", {}).get("error", {}).get(
                    "message"
                )
            except Exception:
                code, message = None, None
            raise LLMEmbeddingAPIError(e.status, code, message)
        except Exception as e:
            raise LLMEmbeddingAPIError(message=str(e))
