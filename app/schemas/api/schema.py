from typing import Any, Literal, NotRequired, Optional, Dict, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict, List


class InvokeRequest(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")
    query: List[str] = Field(description="검색 쿼리")
    # transaction_id: str = Field(description="트랜잭션 아이디")  -> HEADER 관리가 좋음
    search_type: Optional[bool] = Field(
        description="검색 타입, True: 기본 검색, False: 확장 검색",
        default=True,
    )
    return_type: Optional[int] = Field(
        description="1: product_id List[str], 2: Neo4jSchema", default=1
    )
    user_info_yn: Optional[bool] = Field(description="사용자 정보 포함 여부", default=True)


class InvokeResponse(BaseModel):
    code: int = Field(..., example=200)
    data: Dict[str, Any] = Field(..., example={})


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
