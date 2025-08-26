from typing import Dict, List, Optional

from langchain_openai import OpenAI
from openai import AsyncOpenAI

from openai.types.chat.chat_completion import ChatCompletion

from configs import config as global_config


class OpenAIChatLLM:
    def __init__(
        self, base_url: str, api_key: str, model: str, oai_client: Optional[AsyncOpenAI] = None
    ):
        # TODO: remove base_url, api_key
        self.base_url = base_url or f"{global_config.openai_api_base}/compatible/openai"
        self.api_key = api_key or global_config.openai_api_key

        self.model = model
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.async_client = oai_client

    async def agenerate_response(
        self,
        messages: List[Dict[str, str]],
        response_format=None,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        max_tokens: int = 100,
        model: Optional[int] = None,
        seed: int = 10,
        temperature: Optional[float] = 0.1,
        top_p: Optional[float] = 0.1,
        strict_messages_only: bool = False,
    ) -> ChatCompletion:
        """
        Asynchronously generate a response based on the given messages using OpenAI.
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
        return await self.async_client.chat.completions.create(**params)

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        response_format=None,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        max_tokens: int = 100,
        model: Optional[int] = None,
        seed: int = 10,
        temperature: Optional[float] = 0.1,
        top_p: Optional[float] = 0.1,
        strict_messages_only: bool = False,
    ) -> ChatCompletion:
        """
        Generate a response based on the given messages using OpenAI.

        Args:
            messages (list): List of message dicts containing 'role' and 'content'.
            response_format (str or object, optional): Format of the response. Defaults to "text".
            tools (list, optional): List of tools that the model can call. Defaults to None.
            tool_choice (str, optional): Tool choice method. Defaults to "auto".
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 100.
            model (int, optional): The model to use. Defaults to None.
            strict_messages_only (bool, optional): If true, other parameters except messages are ignored. Defaults to False.

        Returns:
            str: The generated response.
        """

        params = {
            "model": global_config.llm_model if model is None else model,
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
        return self.client.chat.completions.create(**params)


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
