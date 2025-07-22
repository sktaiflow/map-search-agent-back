# src/app/agents/llm_caller.py

import json
import logging
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 이 모듈을 위한 로거 설정
logger = logging.getLogger(__name__)


def call_smartbee(
    messages: List[BaseMessage],
    system_message: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    response_format: Optional[Dict[str, str]] = None,
    expect_json: bool = False,
) -> Union[Dict, Any]:
    """
    SmartBee LLM(ChatOpenAI 래퍼)을 초기화하고 지정된 파라미터로 호출합니다.

    이 함수는 순환 참조 문제를 방지하기 위해 독립된 파일로 분리되었습니다.
    메시지 포맷팅, 도구 바인딩, 구조화된 출력, JSON 파싱 등을 처리합니다.

    Args:
        messages (List[BaseMessage]): LLM에 전달할 메시지 목록입니다.
        system_message (Optional[str]): 메시지 목록 앞에 추가할 시스템 프롬프트입니다.
        tools (Optional[List[Any]]): LLM이 사용할 수 있도록 제공할 도구 목록입니다.
        response_format (Optional[Dict[str, str]]): 원하는 응답 형식입니다. (예: {"type": "json_object"})
        expect_json (bool): True일 경우, LLM 응답 내용을 JSON으로 파싱하려고 시도합니다.

    Returns:
        Union[Dict, Any]: LLM의 응답입니다. JSON 파싱에 성공하면 dict, 그렇지 않으면 원본 응답 객체를 반환합니다.
    """
    try:
        # LLM 모델 초기화
        llm = ChatOpenAI(
            model="gpt-4o",
            openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
            temperature=0,
            streaming=False,  # 스트리밍 설정은 호출 방식에 따라 다를 수 있으나, 기본값으로 유지
        )

        # 도구가 제공되면 모델에 바인딩
        if tools:
            llm = llm.bind_tools(tools)

        # JSON 응답 형식이 지정된 경우, 구조화된 출력으로 설정
        if response_format and response_format.get("type") == "json_object":
            # Pydantic 모델이 아닌 일반 dict 스키마를 사용하는 경우
            llm = llm.with_structured_output(method="json_mode")
        else:
            # ✅ JSON 모드가 아닐 때 (일반 텍스트 응답)는 스트리밍을 비활성화합니다.
            # 이렇게 하면 .invoke()가 완전한 AIMessage 객체를 반환하도록 보장됩니다.
            llm.streaming = False

        # 시스템 메시지가 있으면 메시지 목록의 맨 앞에 추가
        if system_message:
            messages.insert(0, SystemMessage(content=system_message))

        # LLM 호출
        response = llm.invoke(messages)

        # JSON 응답을 기대하는 경우
        if expect_json:
            # response는 이제 항상 dict입니다.
            return response if isinstance(response, dict) else {}
        else:
            # response는 이제 항상 AIMessage 객체입니다.
            return response.content if hasattr(response, 'content') else ""

    except Exception as e:
        logger.exception("call_smartbee 함수 실행 중 에러 발생")
        if expect_json:
            return {}
        # AIMessage가 아닌 일반 텍스트를 기대하는 경우 빈 문자열 반환
        return "" if not expect_json else None