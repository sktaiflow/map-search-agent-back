from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal, Union


class Neo4jSearchRequest(BaseModel):
    """
    Neo4j 자연어 검색 요청 스키마
    사용자의 자연어 질문을 받아서 Neo4j 그래프 데이터베이스 검색
    """
    query: str = Field(
        ...,
        description="자연어 검색 쿼리",
        examples=["무제한 데이터 요금제 찾아줘", "할인 혜택이 있는 상품 보여줘"]
    )
    expand_search: bool = Field(
        default=True,
        description="검색 실패시 조건 완화 검색 수행 여부 (case1: 정확매치, case2: 조건완화)"
    )


class CypherRequest(BaseModel):
    """
    Cypher 쿼리 요청 스키마
    클라이언트가 Neo4j에 실행할 Cypher 쿼리를 전송할 때 사용합니다.
    """
    query: str = Field(
        ...,
        description="실행할 Cypher 쿼리문",
        examples=["MATCH (n:요금제) RETURN n.name LIMIT 10"],
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cypher 쿼리에서 사용할 파라미터 (선택사항)",
        examples=[{"name": "John", "age": 30}],
    )
    database: Optional[str] = Field(
        default="neo4j",
        description="대상 DB (미지정 시 기본 DB)",
        examples=["neo4j"],
    )
    access_mode: Literal["r", "w"] = Field(
        default="r",
        description="세션 접근 모드: 읽기(r) / 쓰기(w)",
    )


class CypherResponse(BaseModel):
    """
    Cypher 쿼리 응답 스키마
    Neo4j에서 쿼리 실행 결과를 클라이언트에게 반환할 때 사용합니다.
    """
    data: List[Dict[str, Any]] = Field(default_factory=list, description="쿼리 실행 결과 데이터")
    message: Optional[str] = Field(default=None, description="추가 메시지 (에러 메시지 등)")
    record_count: int = Field(default=0, description="반환된 레코드 수")
    database: Optional[str] = Field(default='neo4j', description="query 대상 DB")
    
    # Neo4j Search Tool 전용 필드들
    case: Optional[str] = Field(default=None, description="검색 케이스 (1: 정확매치, 2: 조건완화)")
    cypher: Optional[Union[str, List[str]]] = Field(default=None, description="실행된 Cypher 쿼리")
    execution_time: Optional[int] = Field(default=None, description="실행 시간 (ms)")
