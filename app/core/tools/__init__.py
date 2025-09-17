from __future__ import annotations

from typing import Any, Dict, List, Sequence

from langchain_core.utils.function_calling import convert_to_openai_function
from pydantic import BaseModel

from app import logger

from app.core.tools.protocol import ToolKitCollectorProtocol
from app.core.tools.utils import SafeValidationTool

__all__ = ["ToolExecutor"]


class ToolExecutor:
    """여러 툴 콜렉터에서 툴을 수집하고 메타정보를 제공하는 실행기."""

    def __init__(
        self,
        collectors: Sequence[ToolKitCollectorProtocol[SafeValidationTool]],
        extra_tools: Sequence[SafeValidationTool] | None = None,
    ):
        self._collectors = list(collectors)
        self._extra_tools = list(extra_tools or [])
        self._tools_cache: List[SafeValidationTool] | None = None
        self._openai_cache: List[Dict[str, Any]] | None = None
        self._description_cache: List[Dict[str, Any]] | None = None

    def refresh(self) -> None:
        """캐시를 초기화해 툴 목록을 다시 수집하도록 한다."""

        self._tools_cache = None
        self._openai_cache = None
        self._description_cache = None

    def get_tools(self) -> List[SafeValidationTool]:
        """사용 가능한 툴 인스턴스 목록을 반환한다."""

        if self._tools_cache is None:
            tools: List[SafeValidationTool] = []
            for collector in self._collectors:
                try:
                    tools.extend(list(collector.get_valid_tools()))
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        message="툴 수집 중 오류 발생",
                        exc_info=exc,
                        type="tool_collector",
                    )
            tools.extend(self._extra_tools)
            unique_tools: Dict[str, SafeValidationTool] = {}
            for tool in tools:
                key = getattr(tool, "name", tool.__class__.__name__)
                unique_tools[key] = tool
            self._tools_cache = list(unique_tools.values())
        return self._tools_cache

    def get_tool(self, name: str) -> SafeValidationTool | None:
        """이름으로 단일 툴을 찾아 반환한다."""

        for tool in self.get_tools():
            if getattr(tool, "name", None) == name or tool.__class__.__name__ == name:
                return tool
        return None

    def get_tools_description(self) -> List[Dict[str, Any]]:
        """LLM 프롬프트용으로 사용할 툴 설명 목록을 생성한다."""

        if self._description_cache is None:
            descriptions: List[Dict[str, Any]] = []
            for tool in self.get_tools():
                descriptions.append(
                    {
                        "name": getattr(tool, "name", tool.__class__.__name__),
                        "description": getattr(tool, "description", ""),
                        "args_schema": self._extract_args_schema(tool),
                    }
                )
            self._description_cache = descriptions

        return self._description_cache

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """OpenAI function-call 형식으로 변환된 툴 정의를 반환한다."""

        if self._openai_cache is None:
            self._openai_cache = [
                convert_to_openai_function(tool) for tool in self.get_tools()
            ]
        return self._openai_cache

    @staticmethod
    def _extract_args_schema(tool: SafeValidationTool) -> Dict[str, Any] | None:
        """툴의 ArgsSchema를 JSON Schema 형태로 정리한다."""

        schema = getattr(tool, "args_schema", None)
        if schema is None:
            return None

        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_json_schema()
        if isinstance(schema, BaseModel):
            return schema.model_json_schema()
        if hasattr(schema, "model_json_schema"):
            return schema.model_json_schema()  # type: ignore[no-any-return]
        if hasattr(schema, "schema"):
            return schema.schema()  # type: ignore[no-any-return]
        return None
