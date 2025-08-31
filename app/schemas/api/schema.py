from typing import Any, Literal, NotRequired, Optional, Dict, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict, List


class InvokeRequest(BaseModel):
    user_id: str = Field(description="유저의 서비스 관리번호 또는 유저ID")
    query: List[str] = Field(description="사용자 발화. 이전 발화 포함시 2개 이상, 아닐 경우 1개")
    expand_search: bool = Field(
        description="case_1: 정확 일치만, case_2: 확장 검색 허용", 
        default=True
    )
    return_type: Optional[int] = Field(
        description="0: neo4j schema 검색결과, 1: product id list만", 
        default=0
    )
    user_info: Optional[bool] = Field(
        description="true: user 정보 조회 tool 사용, false: 사용 안함", 
        default=True
    )


class InvokeResponse(BaseModel):
    code: int = Field(..., example=200)
    data: Dict[str, Any] = Field(..., example={})


class InvokeResponseType0(BaseModel):
    """return_type=0: 전체 응답 스키마"""
    insights: str = Field(description="가성비, 사용자 의도 등을 고려한 적절한 답변")
    summary: str = Field(description="검색 결과의 주요 특징과 제한사항 요약")
    reasoning: str = Field(description="추론 과정 근거 설명, 검색 케이스 정보 포함")
    raw_result: Dict[str, Any] = Field(description="검색된 원본 데이터")
    product_meta: List[Dict[str, Any]] = Field(description="Neo4j 상품 정보, 필요한 필드만")
    user_info: List[Dict[str, Any]] = Field(description="MNO cache API 사용자 정보")
    updated_at: str = Field(description="결과 전송 시각")


class InvokeResponseType1(BaseModel):
    """return_type=1: product ID만 응답 스키마"""
    raw_result: Dict[str, Any] = Field(description="검색된 원본 데이터")
    product_meta: List[str] = Field(description="상품 ID 리스트")
    user_info: List[Dict[str, Any]] = Field(description="MNO cache API 사용자 정보")


class SynonymsRequest(BaseModel):
    keywords: List[str] = Field(description="검색 키워드")
    searchOption: Optional[str] = Field(description="검색 옵션")
    threshold: Optional[int] = Field(description="임계값")
    largCtgId: Optional[List[str]] = Field(description="상위 카테고리 아이디")
    utterance: Optional[str] = Field(description="검색 쿼리 문장")
    svcMgmtNum: Optional[str] = Field(description="서비스 관리 번호")
    commYn: Optional[str] = Field(description="공통/단독 조회 여부")


class SynonymsResponse(BaseModel):
    resultList: List[Dict[str, Any]] = Field(description="동의어 결과 리스트")
