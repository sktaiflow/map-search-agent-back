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


def test_llm_local():
    """로컬 설정을 읽어서 LLM을 호출하는 테스트"""  # 1. 설정 로드 테스트
    test_messages = [
        HumanMessage(content="현재 수행할 단계에 맞게 유저의 요청사항에 맞는 tool을 선택해 주세요.")
    ]
    try:
        response = create_chat_completion(
            messages=test_messages, model="124252", is_result=False, timeout=30  # 중간 과정
        )
        print("##########")
        print(response)
    except Exception as e:
        print(e)


def main():
    """메인 함수"""
    test_llm_local()


if __name__ == "__main__":
    main()
