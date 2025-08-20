# llm_client.py
from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
import uuid
from opentelemetry import trace


# ---- 타입 그대로 유지 ----
class ToolCall(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    function: Optional[Dict[str, Any]] = None


class LLMMetadata(BaseModel):
    id: Optional[str] = None
    response: Dict[str, Any] = {}
    usage: Dict[str, Any] = {}


class LLMOutput(BaseModel):
    type: str
    content: str
    tool_calls: List[ToolCall] = []
    metadata: LLMMetadata = LLMMetadata()


# -------------------------


def _default_headers() -> Dict[str, str]:
    rid = uuid.uuid4().hex[:16]
    span = trace.get_current_span().get_span_context()
    return {
        "X-TRANSACTION-ID": rid,
        "X-Langfuse-Trace-Id": trace.format_trace_id(span.trace_id),
        "X-Langfuse-Parent-Span-Id": trace.format_span_id(span.span_id),
    }


class LLMClient:
    """
    - ChatOpenAI 생성은 per-call (Factory에서 주입 받은 생성자 사용)
    - 요청별 헤더/timeout/옵션은 acomplete 파라미터로
    """

    def __init__(
        self,
        chat_factory,  # Callable[..., ChatOpenAI]
        headers_provider=_default_headers,  # Callable[[], Dict[str, str]]
        *,
        # 필요 시 공통 기본값을 여기서 받기
        max_retries: int = 1,
    ):
        self._chat_factory = chat_factory
        self._headers_provider = headers_provider
        self._max_retries = max_retries

    def _build_kwargs(
        self,
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        llm_kwargs: Optional[Dict[str, Any]],
        reasoning_effort: str,
        is_result: bool,
        tools: Optional[List[Dict]],
        tool_choice: Optional[str],
        response_format: Optional[Dict],
    ) -> Dict[str, Any]:
        kw: Dict[str, Any] = {"model": str(model), "seed": 0, **(llm_kwargs or {})}

        if any(k in model for k in ("o3", "o1", "o4-mini")):
            kw["reasoning_effort"] = reasoning_effort
        else:
            kw["temperature"] = temperature
            kw["max_tokens"] = max_tokens

        if is_result:
            kw["metadata"] = {"is_result": True}

        if response_format:
            # {"type": "json_object"} | {"type": "text"} | {"type": "markdown"}
            kw["response_format"] = response_format

        if tools:
            kw["tools"] = tools
            if tool_choice:
                if tool_choice in ["auto", "none", "required"]:
                    kw["tool_choice"] = tool_choice
                else:
                    tool_names = [t["function"]["name"] for t in tools]
                    assert tool_choice in tool_names, f"{tool_choice} not in {tool_names}"
                    kw["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}
        return kw

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str = "gpt-4o",
        temperature: float = 0.4,
        max_tokens: int = 8000,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        reasoning_effort: str = "medium",
        is_result: bool = False,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict] = None,
        timeout: int = 20,
        **kwargs,
    ) -> LLMOutput:
        if model is None:
            raise ValueError("Model cannot be None")

        default_headers = self._headers_provider()
        chat = self._chat_factory(
            model=model,
            timeout=timeout,
            default_headers=default_headers,
            max_retries=self._max_retries,
        )

        llm = chat.bind(
            **self._build_kwargs(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                llm_kwargs=llm_kwargs,
                reasoning_effort=reasoning_effort,
                is_result=is_result,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )
        )

        message = llm.invoke(messages)
        has_tools = bool(getattr(message, "tool_calls", None))
        return LLMOutput(
            type="tool" if has_tools else "text",
            content=message.content or "",
            tool_calls=[ToolCall(**tc) for tc in (message.tool_calls or [])],
            metadata=LLMMetadata(
                id=getattr(message, "id", None),
                response=getattr(message, "response_metadata", {}) or {},
                usage=getattr(message, "usage_metadata", {}) or {},
            ),
        )

    async def acomplete(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str = "gpt-4o",
        temperature: float = 0.4,
        max_tokens: int = 8000,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        reasoning_effort: str = "medium",
        is_result: bool = False,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict] = None,
        timeout: int = 20,
        **kwargs,
    ) -> LLMOutput:
        if model is None:
            raise ValueError("Model cannot be None")

        default_headers = self._headers_provider()
        chat = self._chat_factory(
            model=model,
            timeout=timeout,
            default_headers=default_headers,
            max_retries=self._max_retries,
        )

        llm = chat.bind(
            **self._build_kwargs(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                llm_kwargs=llm_kwargs,
                reasoning_effort=reasoning_effort,
                is_result=is_result,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )
        )

        message = await llm.ainvoke(messages)
        has_tools = bool(getattr(message, "tool_calls", None))
        return LLMOutput(
            type="tool" if has_tools else "text",
            content=message.content or "",
            tool_calls=[ToolCall(**tc) for tc in (message.tool_calls or [])],
            metadata=LLMMetadata(
                id=getattr(message, "id", None),
                response=getattr(message, "response_metadata", {}) or {},
                usage=getattr(message, "usage_metadata", {}) or {},
            ),
        )

    def embed(
        self,
        text: str = None,
        texts: list[str] = None,
    ) -> list[float]:
        pass

    async def aembed(
        self,
        text: str = None,
        texts: list[str] = None,
    ) -> list[float]:
        pass
