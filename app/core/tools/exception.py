from typing import Optional, List


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
