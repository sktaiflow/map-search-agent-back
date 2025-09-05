from enum import Enum
from typing import Optional


class ErrorCode(Enum):
    BAD_REQUEST = (400, "유효하지 않은 요청입니다.")
    INTERNAL_SERVER_ERROR = (500, "서버 내부에서 에러가 발생했습니다.")
    AGENT_ERROR = (500, "Agent 내부에서 에러가 발생하였습니다.")

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


class ServerError(Exception):
    def __init__(
        self, error_code: ErrorCode, status_code: Optional[int] = None, message: Optional[str] = ""
    ):
        self.status_code = status_code if status_code else error_code.status_code
        self.code = error_code.name
        self.message = message if message else error_code.message
