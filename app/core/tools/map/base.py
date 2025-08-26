from typing import Type
from app import logger
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError
from typing import List


class SafeValidationTool(BaseTool):
    """
    Pydantic 유효성 검사 실패 시 warning을 로깅하고
    원본 데이터를 반환하는 예외 처리 기능이 추가된 BaseTool
    """

    response_model: Type[BaseModel]

    def _validate_response(self, response: dict) -> dict:
        """
        Pydantic 모델로 응답 데이터의 유효성을 검사하고, 실패 시 예외를 처리합니다.
        """
        try:
            return self.response_model.model_validate(response).model_dump()
        except ValidationError as e:
            logger.warn(
                f"Tool '{self.name}'의 응답 데이터가 Pydantic 모델 '{self.response_model.__name__}'과"
                f" 일치하지 않습니다. 원본 데이터를 그대로 반환합니다. Error: {e}"
            )
            return response


class BaseToolKit:
    """도구들을 관리하는 기본 툴킷 클래스"""

    def __init__(self, map_client, method_api_key: str, status: bool = True):
        self.map_client = map_client
        self.method_api_key = method_api_key

    def get_tools(self) -> List[BaseTool]:
        raise NotImplementedError("Subclasses must implement get_tools method")

    def get_tools_description(self) -> str:
        from app.core.tools.utils import get_tools_description

        tools = self.get_tools()
        return get_tools_description(tools)

    def get_tools_info(self) -> dict:
        """툴킷의 모든 tools 정보를 딕셔너리로 반환"""
        tools = self.get_tools()
        return {tool.name: tool.description for tool in tools}
