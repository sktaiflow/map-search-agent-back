# embedding_client.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings
import numpy as np


class EmbeddingOutput(BaseModel):
    model: str
    vectors: List[float]


class EmbeddingClient:
    """
    - OpenAIEmbeddings 팩토리 주입
    - 배치/비동기/차원 관리/정규화 등 운영 편의 로직 포함
    """

    def __init__(
        self,
        embeddings_factory,  # Callable[..., OpenAIEmbeddings]
        *,
        default_model: str = "text-embedding-3-small",
        default_dimensions: Optional[int] = None,
        normalize: bool = True,
    ):
        self._emb_factory = embeddings_factory
        self._embed_model = default_model
        self._embed_dims = default_dimensions
        self._normalize = normalize

    def _maybe_normalize(self, arr: List[List[float]]) -> List[List[float]]:
        if not self._normalize:
            return arr
        m = np.array(arr, dtype=np.float32)
        norms = np.linalg.norm(m, axis=1, keepdims=True) + 1e-12
        m = m / norms
        return m.tolist()

    # TODO: logger 추가 (assert -> logging, raise -> logging)
    async def aembed(
        self,
        text: str,
        *,
        model: Optional[str] = None,
    ) -> EmbeddingOutput:
        """
        단일 문자열을 입력받아 임베딩 벡터를 반환
        """
        assert self._emb_factory is not None, "embeddings_factory not injected"

        model_to_use = model or self._embed_model

        try:
            vector: list[float] = await self._emb_factory.aembed_query(text)
            print(f"임베딩 성공 - 벡터 길이: {len(vector)}")

            if self._normalize:
                n_vector = self._maybe_normalize([vector])
            else:
                n_vector = [vector]

            return EmbeddingOutput(
                model=model_to_use,
                vectors=n_vector[0],
            )

        except Exception as e:
            raise
