from typing import Dict, List, Union, Callable, runtime_checkable
from typing import Type
from app import logger
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError
from typing import Generic, Sequence, Protocol, TypeVar, runtime_checkable
from configs.default import BaseConfig
from configs import config as global_config


def get_tools_description(tools: list[BaseTool]) -> str:
    return "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)


class SafeValidationTool(BaseTool):
    """
    Pydantic 유효성 검사 실패 시 warning을 로깅하고
    원본 데이터를 반환하는 예외 처리 기능이 추가된 BaseTool
    status: bool = True: 해당 Tool 사용 가능 여부 (True: 사용 가능, False: 사용 불가)
    """

    response_model: Type[BaseModel]
    config: BaseConfig = global_config
    status: bool = True

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

    # 동기 실행도 구현하려면 이 부분을 없애고 구현
    def _run(self, *args, **kwargs):
        raise NotImplementedError("Use async _arun()")
