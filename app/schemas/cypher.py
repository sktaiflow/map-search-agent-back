"""
Cypher API용 Pydantic 스키마 정의
이 파일은 Cypher 쿼리 요청과 응답의 데이터 구조를 정의합니다.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CypherRequest(BaseModel):
    """
    Cypher 쿼리 요청 스키마
    클라이언트가 Neo4j에 실행할 Cypher 쿼리를 전송할 때 사용합니다.
    """
    query: str = Field(
        ..., 
        description="실행할 Cypher 쿼리문",
        example="MATCH (n:Person) RETURN n.name LIMIT 10"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cypher 쿼리에서 사용할 파라미터 (선택사항)",
        example={"name": "John", "age": 30}
    )


class CypherResponse(BaseModel):
    """
    Cypher 쿼리 응답 스키마
    Neo4j에서 쿼리 실행 결과를 클라이언트에게 반환할 때 사용합니다.
    """
    success: bool = Field(
        ..., 
        description="쿼리 실행 성공 여부"
    )
    data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="쿼리 실행 결과 데이터"
    )
    message: Optional[str] = Field(
        default=None,
        description="추가 메시지 (에러 메시지 등)"
    )
    record_count: int = Field(
        default=0,
        description="반환된 레코드 수"
    )
