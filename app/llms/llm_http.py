from typing import Dict, List, Optional, Any, Literal, Union

import json
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI

from openai.types.chat.chat_completion import ChatCompletion
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from configs import config as global_config


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)  # 파싱된 dict
    raw_arguments: str  # 원본 JSON 문자열


class LLMResult(BaseModel):
    """
    - tool이면 tool_calls에 실행 가능한 구조로 들어있음
    - chat이면 message 자연어 응답
    - assistant_message_for_history: 히스토리에 그대로 append할 원본 assistant 메시지
    - raw_response: 원본 전체(로깅/디버깅용)
    """

    is_toolcall: bool = Field(default=False, description="tool call 여부")
    message: Optional[str] = Field(default=None, description="자연어 chat 응답")
    tool_calls: List[ToolCall] = Field(default_factory=list)
    assistant_message_for_history: Dict[str, Any]
    raw_response: Dict[str, Any]


def _to_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return json.loads(getattr(obj, "json")())


def parse_chat_completion(resp: Any) -> LLMResult:
    """
    LLM 응답을 parsing 후 toolcall인지 chat인지 판단 후 표준화해서 반환
    - tool_calls 있으면 is_toolcall=True
    - 없으면 일반 챗 응답
    """
    response = _to_dict(resp)
    choices = response.get("choices", [])
    msg = (choices[0].get("message") if choices else {}) or {}

    tool_calls_raw = msg.get("tool_calls") or []
    content = msg.get("content")

    if tool_calls_raw:
        parsed_calls: List[ToolCall] = []
        for tc in tool_calls_raw:
            fn = tc.get("function", {}) or {}
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except Exception:
                args = {}
            parsed_calls.append(
                ToolCall(
                    id=tc.get("id") or "",
                    name=fn.get("name") or "",
                    raw_arguments=raw_args,
                    arguments=args,
                )
            )
        return LLMResult(
            is_toolcall=True,
            message=None,
            tool_calls=parsed_calls,
            assistant_message_for_history=msg,
            raw_response=response,
        )

    return LLMResult(
        is_toolcall=False,
        message=content or "",
        tool_calls=[],
        assistant_message_for_history=msg,
        raw_response=response,
    )


class OpenAIChatLLM:
    def __init__(
        self, base_url: str, api_key: str, model: str, oai_client: Optional[AsyncOpenAI] = None
    ):
        # TODO: remove base_url, api_key
        self.base_url = base_url or f"{global_config.openai_api_base}"
        self.api_key = api_key or global_config.openai_api_key

        self.model = model
        self.client = ChatOpenAI(api_key=api_key, base_url=base_url, model=model)
        self.async_client = oai_client

    async def agenerate_response(
        self,
        messages: List[Dict[str, str]],
        response_format=None,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        max_tokens: int = 100,
        model: Optional[Union[int, str]] = None,
        seed: int = 10,
        temperature: Optional[float] = 0.1,
        top_p: Optional[float] = 0.1,
        strict_messages_only: bool = False,
    ) -> LLMResult:
        """
        Asynchronously generate a response based on the given messages using OpenAI.
        Returns parsed LLMResult with tool calls or chat response.
        """
        params = {
            "model": self.model if model is None else model,
            "messages": messages,
        }

        if strict_messages_only is False:
            params.update(
                {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    **({"response_format": response_format} if response_format else {}),
                    **({"tools": tools} if tools else {}),
                    **({"tool_choice": tool_choice} if tools else {}),
                    **({"seed": seed} if seed else {}),
                }
            )

        # OpenAI API 호출
        resp = await self.async_client.chat.completions.create(**params)
        return parse_chat_completion(resp)


# import json
# import logging
# import os
# from typing import Any, Dict, List, Optional, Union
# from configs import config

# from langchain_core.messages import BaseMessage, SystemMessage
# from langchain_openai import ChatOpenAI
# from opentelemetry import trace
# import uuid
# from .request_handler import get_request_id
# from app.schemas.llm import LLMOutput, LLMMetadata, ToolCall


# async def async_create_chat_completion(
#     messages: List[Dict[str, str]],
#     model: str | None = "gpt-4o",
#     temperature: float = 0.4,
#     max_tokens: int = 8000,
#     llm_kwargs: Dict[str, Any] = None,
#     reasoning_effort: str = "medium",
#     is_result: bool = False,
#     tools: List[Dict] = None,
#     tool_choice: str = None,
#     response_format: Dict = None,
#     timeout: int = 20,
#     **kwargs,
# ) -> str:

#     # validate input
#     if model is None:
#         raise ValueError("Model cannot be None")

#     # Get the provider from supported providers
#     kwargs = {"model": str(model), "seed": 0, **(llm_kwargs or {})}

#     ## 추론모델에는 파라미터 추가
#     if "o3" in model or "o1" in model or "o4-mini" in model:
#         kwargs["reasoning_effort"] = reasoning_effort
#     else:
#         kwargs["temperature"] = temperature
#         kwargs["max_tokens"] = max_tokens

#     ## 최종 결과물임을 표시하는 파라미터
#     if is_result:
#         kwargs["metadata"] = {"is_result": True}

#     ## json_object , text, markdown 형식 지정
#     # {"type": "json_object"}
#     # {"type": "text"}
#     # {"type": "markdown"}
#     if response_format:
#         kwargs["response_format"] = response_format

#     if tools:
#         kwargs["tools"] = tools
#         if tool_choice:
#             kwargs["tool_choice"] = tool_choice
#             if tool_choice not in ["auto", "none", "required"]:
#                 tool_names = [tool["function"]["name"] for tool in tools]
#                 assert (
#                     tool_choice in tool_names
#                 ), f"Tool choice {tool_choice} not in tools {tool_names}"
#                 kwargs["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}

#     llm = ChatOpenAI(
#         model=model,
#         base_url=config.openai_api_base,
#         api_key=config.openai_api_key,
#         disable_streaming=True,
#         max_retries=1,
#         timeout=timeout,
#     ).bind(**kwargs)

#     message = await llm.ainvoke(messages)
#     has_tools = bool(getattr(message, "tool_calls", None))
#     return LLMOutput(
#         type="tool" if has_tools else "text",
#         content=message.content or "",
#         tool_calls=[ToolCall(**tc) for tc in (message.tool_calls or [])],
#         metadata=LLMMetadata(
#             id=getattr(message, "id", None),
#             response=getattr(message, "response_metadata", {}) or {},
#             usage=getattr(message, "usage_metadata", {}) or {},
#         ),
#     )


# def create_chat_completion(
#     messages: List[Dict[str, str]],
#     model: str | None = "gpt-4o",
#     temperature: float = 0,
#     max_tokens: int = 8000,
#     llm_kwargs: Dict[str, Any] = None,
#     reasoning_effort: str = "medium",
#     is_result: bool = False,
#     tools: List[Dict] = None,
#     tool_choice: str = None,
#     response_format: Dict = None,
#     timeout: int = 20,
#     **kwargs,
# ) -> str:

#     # validate input
#     if model is None:
#         raise ValueError("Model cannot be None")

#     # Get the provider from supported providers
#     kwargs = {"model": str(model), "seed": 0, **(llm_kwargs or {})}

#     ## 추론모델에는 파라미터 추가
#     if "o3" in model or "o1" in model or "o4-mini" in model:
#         kwargs["reasoning_effort"] = reasoning_effort
#     else:
#         kwargs["temperature"] = temperature
#         kwargs["max_tokens"] = max_tokens

#     ## 최종 결과물임을 표시하는 파라미터
#     if is_result:
#         kwargs["metadata"] = {"is_result": True}

#     ## json_object , text, markdown 형식 지정
#     # {"type": "json_object"}
#     # {"type": "text"}
#     # {"type": "markdown"}
#     if response_format:
#         kwargs["response_format"] = response_format

#     if tools:
#         kwargs["tools"] = tools
#         if tool_choice:
#             kwargs["tool_choice"] = tool_choice
#             if tool_choice not in ["auto", "none", "required"]:
#                 tool_names = [tool["function"]["name"] for tool in tools]
#                 assert (
#                     tool_choice in tool_names
#                 ), f"Tool choice {tool_choice} not in tools {tool_names}"
#                 kwargs["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}

#     if not config.openai_api_key:
#         config.openai_api_key = "NONE"

#     llm = ChatOpenAI(
#         model=model,
#         base_url=config.openai_api_base,
#         api_key=config.openai_api_key,
#         default_headers={},
#         max_retries=1,
#         timeout=timeout,
#     ).bind(**kwargs)

#     message = llm.invoke(messages)

#     has_tools = bool(getattr(message, "tool_calls", None))
#     return LLMOutput(
#         type="tool" if has_tools else "text",
#         content=message.content or "",
#         tool_calls=[ToolCall(**tc) for tc in (message.tool_calls or [])],
#         metadata=LLMMetadata(
#             id=getattr(message, "id", None),
#             response=getattr(message, "response_metadata", {}) or {},
#             usage=getattr(message, "usage_metadata", {}) or {},
#         ),
#     )
