# llm_client.py
from typing import Any, Dict, List, Optional, Union
from langchain_core.runnables import Runnable, RunnablePassthrough
import uuid
from opentelemetry import trace
from app.llms.schema import ToolCall, LLMMetadata, LLMOutput
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from functools import reduce
import operator


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

    def _build_llm_runnable(
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
        timeout: int,
    ) -> Runnable:
        """
        공통: ChatOpenAI 인스턴스를 per-call로 만들고 bind된 Runnable을 반환
        """
        default_headers = self._headers_provider()

        llm: Runnable = self._chat_factory.bind(
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
        return llm

    def _normalize_to_llm_output(self, message: Any) -> LLMOutput:
        if isinstance(message, BaseMessage):
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
        else:
            return LLMOutput(
                type="text",
                content=(
                    message if isinstance(message, str) else ("" if message is None else message)
                ),
                tool_calls=[],
                metadata=LLMMetadata(id=None, response={}, usage={}),
            )

    def build_chain(
        self,
        *,
        prompt: Optional[Runnable] = None,
        llm: Optional[Runnable] = None,
        parser: Optional[Runnable] = None,
        fallback_when_no_prompt: bool = True,
    ) -> Runnable:
        """
        주어진 컴포넌트만으로 Runnable 체인을 동적으로 구성.
        - prompt | llm | parser 형태를 가능한 부분까지만 연결
        - prompt가 없으면 기본적으로 입력을 그대로 llm에 전달 (Passthrough)
        """
        parts: list[Runnable] = []

        if prompt is not None:
            parts.append(prompt)
        elif fallback_when_no_prompt:
            # 입력(dict/str/messages)을 그대로 다음 단계로 넘김
            parts.append(RunnablePassthrough())

        if llm is not None:
            parts.append(llm)

        if parser is not None:
            parts.append(parser)

        if not parts:
            raise ValueError("At least one of prompt/llm/parser must be provided.")

        return reduce(operator.or_, parts)

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        prompt: Optional[Runnable] = None,
        parser: Optional[Runnable] = None,
        model: str = "gpt-4o",
        temperature: float = 0.4,
        max_tokens: int = 8000,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        reasoning_effort: str = "medium",
        is_result: bool = False,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict] = {"type": "json_object"},
        timeout: int = 20,
        **kwargs,
    ) -> LLMOutput:
        if model is None:
            raise ValueError("Model cannot be None")

        llm = self._build_llm_runnable(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            llm_kwargs=llm_kwargs,
            reasoning_effort=reasoning_effort,
            is_result=is_result,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            timeout=timeout,
        )
        chain = self.build_chain(prompt=prompt, llm=llm, parser=parser)
        message = chain.invoke(messages)

        return self._normalize_to_llm_output(message)

    async def acomplete(
        self,
        messages: List[Dict[str, str]],
        *,
        prompt: Optional[Runnable] = None,
        parser: Optional[Runnable] = None,
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

        llm = self._build_llm_runnable(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            llm_kwargs=llm_kwargs,
            reasoning_effort=reasoning_effort,
            is_result=is_result,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            timeout=timeout,
        )
        chain = self.build_chain(prompt=prompt, llm=llm, parser=parser)
        message = await chain.ainvoke(messages)
        return self._normalize_to_llm_output(message)
