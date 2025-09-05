from typing import Any, Literal, NotRequired, Optional, Dict, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict, List


class InvokeRequest(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")
    query: List[str] = Field(description="검색 쿼리")
    expand_search: bool = Field(
        description="case_1: 정확 일치만, case_2: 확장 검색 허용", default=True
    )

    return_type: Optional[int] = Field(
        description="0: neo4j schema 검색결과, 1: product id list만", default=0
    )
    user_info: Optional[bool] = Field(
        description="true: user 정보 조회 tool 사용, false: 사용 안함", default=True
    )


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
