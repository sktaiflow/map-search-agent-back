from typing import Type
from app import logger
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError


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
