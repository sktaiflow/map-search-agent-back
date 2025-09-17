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
        self,
        base_url: str,
        api_key: str,
        model: str,
        oai_client: Optional[AsyncOpenAI] = None,
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
