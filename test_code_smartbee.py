import asyncio
import os
from dotenv import load_dotenv
from app.clients.http_base import HTTPBaseClient, ClientTimeout, Retry
from app.llms.embedding_llm_http import OpenAIEmbeddingModel
from app.llms.llm_http import OpenAIChatLLM
import httpx
from openai import AsyncOpenAI, OpenAI


# .env 파일 로드
load_dotenv()
OPENAI_API_BASE = "https://aihub-api.sktelecom.com/aihub/v2/sandbox"
OPENAI_API_KEY = "e97ee307-a791-4e06-ade1-df4b9d032eed"


async def test_embedding_client():
    """임베딩 클라이언트 테스트"""

    # HTTP 클라이언트 설정
    http_client = HTTPBaseClient(
        session=None,  # 테스트용이므로 None
        timeout=ClientTimeout(connect=5.0, sock_connect=5.0, sock_read=30.0),
        retry=Retry(total=3, base=1.0, cap=10.0),
    )

    # 임베딩 모델 초기화
    embedding_model = OpenAIEmbeddingModel(
        http_client=http_client,
        host=OPENAI_API_BASE,
        api_key=OPENAI_API_KEY,
        model="text-embedding-3-small",
    )

    # 테스트 쿼리
    test_query = "안녕하세요, 지도 검색 에이전트입니다."

    try:
        print(f"테스트 쿼리: {test_query}")
        print("임베딩 생성 중...")

        # 단일 텍스트 임베딩
        embed_response = await embedding_model.aembed(text=test_query)
        embeddings = embed_response.embeddings
        print(embeddings)
    except Exception as e:
        print(f"임베딩 실패: {e}")
        print(f"에러 타입: {type(e)}")


async def test_chatcompletion_client():
    # HTTP 클라이언트 설정
    limits = httpx.Limits(max_keepalive_connections=2048, max_connections=2048, keepalive_expiry=10)
    timeout = httpx.Timeout(pool=1.0, connect=1, read=14, write=None)

    # AsyncOpenAI 클라이언트 생성
    oai_client = AsyncOpenAI(
        base_url=OPENAI_API_BASE,
        api_key=OPENAI_API_KEY,
        http_client=httpx.AsyncClient(limits=limits, timeout=timeout),
    )
    # # OpenAIChatLLM 클라이언트 생성
    llm_client = OpenAIChatLLM(
        base_url=f"{OPENAI_API_BASE}",
        api_key=OPENAI_API_KEY,
        model="gpt-4o",
        oai_client=oai_client,
    )

    # # 채팅 완료 요청 생성
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ]

    response = await llm_client.agenerate_response_petool(messages=messages)
    print(response)


if __name__ == "__main__":
    print("=== 임베딩 클라이언트 테스트 시작 ===")

    # 기본 임베딩 테스트
    asyncio.run(test_embedding_client())

    print("\n" + "=" * 50 + "\n")

    # HTTP 클라이언트 테스트
    asyncio.run(test_with_httpx_client())

    print("=== 채팅 완료 클라이언트 테스트 시작 ===")
    asyncio.run(test_chatcompletion_client())
    print("\n=== 테스트 완료 ===")
