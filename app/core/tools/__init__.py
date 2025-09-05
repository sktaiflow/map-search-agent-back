from typing import Any, Dict, List, Callable, Union, Optional

from app.core.tools.utils import SafeValidationTool
from app import logger


class ToolExecutionError(Exception):
    """툴 실행 관련 예외"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.available_tools = available_tools


class ToolNotFoundError(ToolExecutionError):
    """툴 못찾는 경우"""

    pass


class ToolDisabledError(ToolExecutionError):
    """툴이 비활성화된 경우"""

    pass


def execute_tool(
    tool_name_mapping: Dict[str, SafeValidationTool], tool_name: str, tool_arguments: Dict[str, Any]
) -> Any:
    """
    툴 실행 함수 - 동기 실행 (예외 기반)
    Args:
        tool_name_mapping: 툴 이름 -> 툴 객체 매핑
        tool_name: 실행할 툴 이름
        tool_arguments: 툴 실행 인자
    Returns:
        툴 실행 결과 (성공 시에만)
    """
    tool = tool_name_mapping.get(tool_name)

    if tool is None:
        raise ToolNotFoundError(
            f"Tool '{tool_name}' not found",
            tool_name=tool_name,
            available_tools=list(tool_name_mapping.keys()),
        )

    if not getattr(tool, "status", True):
        raise ToolDisabledError(f"Tool '{tool_name}' is currently disabled", tool_name=tool_name)

    try:
        result = tool._run(**tool_arguments)
        if hasattr(tool, "_validate_response") and isinstance(result, dict):
            result = tool._validate_response(result)
        return result
    except Exception as e:
        logger.error(
            type="tool call error", message=f"Tool execution failed: {tool_name}", exc_info=e
        )
        raise ToolExecutionError(f"Tool execution failed: {str(e)}", tool_name=tool_name) from e


async def execute_tool_async(
    tool_name_mapping: Dict[str, SafeValidationTool], tool_name: str, tool_arguments: Dict[str, Any]
) -> Any:
    """
    툴 실행 함수 - 비동기 실행
    """
    tool = tool_name_mapping.get(tool_name)

    if tool is None:
        raise ToolNotFoundError(
            f"Tool '{tool_name}' not found",
            tool_name=tool_name,
            available_tools=list(tool_name_mapping.keys()),
        )

    if not getattr(tool, "status", True):
        raise ToolDisabledError(f"Tool '{tool_name}' is currently disabled", tool_name=tool_name)
    try:
        if hasattr(tool, "_arun"):
            result = await tool._arun(**tool_arguments)
        else:
            raise ToolExecutionError(f"Tool '{tool_name}' does not support async execution")

        if hasattr(tool, "_validate_response") and isinstance(result, dict):
            result = tool._validate_response(result)

        return result

    except Exception as e:
        logger.error(
            type="tool call error", message=f"Tool execution failed: {tool_name}", exc_info=e
        )
        raise ToolExecutionError(f"Tool execution failed: {str(e)}", tool_name=tool_name) from e


def create_tool_executor(tool_name_mapping: Dict[str, SafeValidationTool]) -> Callable:
    """
    동기 툴 실행기 팩토리 함수

    Args:
        tool_name_mapping: 툴 이름 -> 툴 객체 매핑

    Returns:
        동기 Callable 함수
    """

    def executor(tool_name: str, tool_arguments: Dict[str, Any]) -> Any:
        return execute_tool(tool_name_mapping, tool_name, tool_arguments)

    return executor


def create_async_tool_executor(tool_name_mapping: Dict[str, SafeValidationTool]) -> Callable:
    """
    비동기 툴 실행기 팩토리 함수

    Args:
        tool_name_mapping: 툴 이름 -> 툴 객체 매핑

    Returns:
        비동기 Callable 함수
    """

    async def async_executor(tool_name: str, tool_arguments: Dict[str, Any]) -> Any:
        return await execute_tool_async(tool_name_mapping, tool_name, tool_arguments)

    return async_executor


def create_agent_tools_data(tool_collectors: List[Any]) -> Dict[str, Any]:
    """
    여러 툴 컬렉터들로부터 통합 툴 데이터를 생성

    Args:
        tool_collectors: 툴 컬렉터들의 리스트

    Returns:
        통합된 툴 데이터 딕셔너리
    """

    # 모든 컬렉터에서 유효한 툴들 수집
    all_tools: List[SafeValidationTool] = []
    all_openai_tools: List[dict] = []
    all_descriptions: List[str] = []

    for collector in tool_collectors:
        collector_name = type(collector).__name__
        try:
            # tool protocol check 및 callable 확인
            if hasattr(collector, "get_valid_tools") and callable(collector.get_valid_tools):
                tools = collector.get_valid_tools()
            elif hasattr(collector, "valid_tools"):
                tools = collector.valid_tools
            else:
                raise

            if tools:
                all_tools.extend(tools)

            # OpenAI 포맷 tools 변환
            if hasattr(collector, "get_valid_tools_with_openai_function"):
                openai_tools = collector.get_valid_tools_with_openai_function()
                if openai_tools:
                    all_openai_tools.extend(openai_tools)

            # 툴 설명 수집 -> Planning prompt 생성에 사용
            if hasattr(collector, "get_tools_description"):
                description = collector.get_tools_description()
                if description:
                    all_descriptions.append(description)

        except Exception as e:
            logger.error(
                type="tool collator",
                message=f"Error collecting tools from {collector_name}",
                exc_info=e,
            )
            raise

    # status 한번더 확인
    active_tools = [tool for tool in all_tools if getattr(tool, "status", True)]

    tool_name_mapping: Dict[str, SafeValidationTool] = {}
    for tool in active_tools:
        if tool.name in tool_name_mapping:
            logger.warn(f"Duplicate tool name detected: {tool.name}")
            continue
        tool_name_mapping[tool.name] = tool

    # 통합 툴 설명 생성
    unified_description = "\n".join(all_descriptions) if all_descriptions else ""

    return {
        "openai_tools": all_openai_tools,
        "tools_description": unified_description,
        "tool_name_mapping": tool_name_mapping,
        "tool_executor": create_tool_executor(tool_name_mapping),
        "tool_executor_async": create_async_tool_executor(tool_name_mapping),
        "tool_names": list(tool_name_mapping.keys()),
        "tool_count": len(active_tools),
    }


__all__ = [
    "create_agent_tools_data",
    "execute_tool",
    "execute_tool_async",
    "create_tool_executor",
    "create_async_tool_executor",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolDisabledError",
]
