"""
Tool 시스템의 기본 구조 정의

이 파일의 목적:
- 모든 툴에서 반복되는 보일러플레이트 코드를 한 곳으로 통합
- 툴킷별로 분산된 인터페이스를 일관된 형태로 표준화
- Langchain 생태계와의 호환성 보장
- 단순하고 확장 가능한 구조 제공
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError
from app import logger


# 명확한 에러 구분을 위한 전용 예외 클래스들
class ToolExecutionError(Exception):
    """툴 실행 중 발생하는 에러"""
    pass


class ToolValidationError(Exception):
    """툴 입력/출력 검증 실패 에러"""
    pass


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
    response_model: Type[BaseModel] = None
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
    
    def _validate_response(self, response: dict) -> dict:
        """
        응답 데이터를 Pydantic 모델로 검증
        
        왜 이 기능이 필요한가?
        - 외부 API(MAP, Neo4j) 응답이 예상과 다를 수 있어서 검증 필요
        - 검증 실패 시에도 시스템이 중단되지 않고 원본 데이터 반환
        - 기존 SafeValidationTool의 핵심 기능을 그대로 유지
        """
        if not self.response_model:
            return response
            
        try:
            return self.response_model.model_validate(response).model_dump()
        except ValidationError as e:
            logger.warning(
                f"Tool '{self.name}'의 응답 데이터가 예상 형식과 다릅니다. "
                f"원본 데이터를 반환합니다. Error: {e}"
            )
            return response


class ToolKitBase(ABC):
    """
    모든 툴킷이 상속받을 통합된 기본 인터페이스
    
    왜 이 인터페이스가 필요한가?
    - 기존 MAPBaseToolKit, SearchBaseToolKit이 서로 다른 인터페이스를 가져서 일관성 부족
    - 새로운 도메인(payment, search 등) 추가 시마다 새로운 base 클래스를 만드는 문제 해결
    - 모든 툴킷이 동일한 방식으로 사용될 수 있도록 표준화
    """
    
    @abstractmethod
    def get_available_tools(self) -> List[StandardizedTool]:
        """
        현재 사용 가능한 툴 목록 반환
        
        왜 이 메서드가 필요한가?
        - status=True인 툴만 필터링해서 반환
        - 모든 툴킷에서 일관된 타입(StandardizedTool) 반환 보장
        """
        pass
    
    @abstractmethod 
    def get_tools_description(self) -> str:
        """
        LLM이 planning할 때 사용할 툴 설명 문자열 생성
        
        왜 문자열 형태인가?
        - plan_node에서 LLM에게 프롬프트로 전달하기 위함
        - "tool_name: tool_description" 형태로 개행 연결된 읽기 쉬운 형식
        """
        pass
    
    def get_tools_for_langchain(self) -> List[Dict[str, Any]]:
        """
        Langchain의 bind_tools에서 사용할 수 있는 형태로 툴 정보 변환
        
        왜 이 기능이 필요한가?
        - 향후 Tool Calling 방식으로 전환할 때를 대비
        - Langchain의 convert_to_openai_function을 활용해 표준 변환
        - 각 툴킷마다 이 변환 로직을 중복 구현하지 않도록 공통 제공
        """
        from langchain_core.utils.function_calling import convert_to_openai_function
        
        try:
            tools = self.get_available_tools()
            return [convert_to_openai_function(tool) for tool in tools]
        except Exception as e:
            logger.error(f"Langchain 툴 변환 실패: {str(e)}")
            raise ToolExecutionError(f"Failed to convert tools for Langchain: {str(e)}") from e