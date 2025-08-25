# test_llm_local.py
import os
import sys
import asyncio
from pathlib import Path
from configs import config
from app.core.llm import create_chat_completion
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    FunctionMessage,
)
from langgraph.prebuilt import create_react_agent
from app.llms.llm import LLMClient

from langchain_openai import ChatOpenAI
from app.core.prompts import PLANNING_PROMPT

OPENAI_API_BASE = "https://aide.dev.apollo-lunar.com/pe-proxy/api/v1/compatible/openai"
# OPENAI_BASE_URL=https://aihub-api.sktelecom.com/aihub/v2/sandbox
OPENAI_API_KEY = "e97ee307-a791-4e06-ade1-df4b9d032eed"
from pydantic import SecretStr

LLM_CLIENT = LLMClient(
    ChatOpenAI(base_url=OPENAI_API_BASE, api_key=OPENAI_API_KEY),
    max_retries=1,
)
messages = [
    SystemMessage(content=PLANNING_PROMPT.format(tool_list_json="test")),
    HumanMessage(content=f"사용자 쿼리: 요금제"),
]


async def test_llm_local():
    resp = await LLM_CLIENT.acomplete(messages=messages, model="124252", timeout=30)
    print(resp)
    return resp


result = asyncio.run(test_llm_local())


def main():
    """메인 함수"""
    result = await test_llm_local()  # 결과 받기
    print("최종 결과:", result)


if __name__ == "__main__":
    asyncio.run(main())
