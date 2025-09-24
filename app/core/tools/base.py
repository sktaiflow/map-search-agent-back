"""
Tool 시스템의 기본 구조 정의

이 파일의 목적:
- 모든 개별 툴에서 반복되는 보일러플레이트 코드를 한 곳으로 통합
- Langchain BaseTool과의 호환성 보장
- 일관된 응답 검증 및 에러 처리 제공
- 단순하고 확장 가능한 툴 구조 제공
"""

from typing import Optional, Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from app import logger


class StandardizedTool(BaseTool):
    """
    모든 비즈니스 툴이 상속받을 기본 클래스

    왜 이 클래스가 필요한가?
    - 기존 7개 툴에서 동일하게 반복되던 _run() 메서드 중복 제거
    - SafeValidationTool의 유용한 기능들을 계승하면서 의존성 제거
    - Langchain BaseTool 호환성 보장으로 bind_tools 등에서 사용 가능
    - 각 툴은 핵심 비즈니스 로직(_arun)에만 집중할 수 있음
    """

    # 각 툴에서 정의해야 할 필드들 (기존 SafeValidationTool 패턴 유지)
    response_model: Optional[Any] = None
    status: bool = True

    def _run(self, *args, **kwargs):
        """
        동기 실행 메서드 비활성화

        왜 이렇게 하나?
        - Langchain BaseTool 상속 시 _run 구현이 필수이지만
        - 우리 시스템은 모든 작업이 비동기(HTTP, DB, LLM 호출)라서 동기 실행이 불가능
        - 기존 모든 툴에서 동일한 NotImplementedError를 던지고 있어서 중복 제거
        """
        raise NotImplementedError("Use async _arun() instead")

    def _validate_response(self, response: Any) -> Any:
        """
        응답 데이터를 Pydantic 모델로 검증

        왜 이 기능이 필요한가?
        - 외부 API(MAP, Neo4j) 응답이 예상과 다를 수 있어서 검증 필요
        - 검증 실패 시에도 시스템이 중단되지 않고 원본 데이터 반환
        - 기존 SafeValidationTool의 핵심 기능을 그대로 유지
        """

        logger.info("########### Tool Response ############")
        logger.info(response)
        logger.info("######################################")

        if not self.response_model:
            return response

        try:
            return self.response_model.model_validate(response).model_dump()
        except ValidationError as e:
            logger.warn(
                f"Tool '{self.name}'의 응답 데이터가 예상 형식과 다릅니다. "
                f"원본 데이터를 반환합니다. Error: {e}"
            )
            return response
