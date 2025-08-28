"""
Cypher API 라우터
이 파일은 Cypher 쿼리 실행을 위한 간단한 REST API 엔드포인트를 정의합니다.
"""
import time
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from dependency_injector.wiring import Provide, inject
from neo4j import AsyncDriver, READ_ACCESS
from neo4j.exceptions import Neo4jError

from app.container import Container
from app.schemas.cypher import CypherRequest, CypherResponse
from app import logger

# API 라우터 생성
router = APIRouter(tags=["Cypher Query"])


def convert_neo4j_value(value: Any) -> Any:
    """Neo4j 값을 JSON 직렬화 가능한 형태로 변환"""
    if hasattr(value, 'labels') and hasattr(value, 'items'):
        # Neo4j Node
        return {'labels': list(value.labels), 'properties': dict(value.items())}
    elif hasattr(value, 'type') and hasattr(value, 'items'):
        # Neo4j Relationship
        return {'type': value.type, 'properties': dict(value.items())}
    elif isinstance(value, list):
        return [convert_neo4j_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: convert_neo4j_value(v) for k, v in value.items()}
    else:
        return value


@router.post(
    "/v1/cypher/execute",
    response_model=CypherResponse,
    summary="Cypher 쿼리 실행",
    description="Neo4j 데이터베이스에서 Cypher 쿼리를 실행합니다."
)
@inject
async def execute_cypher_query(
    request: CypherRequest,
    neo4j_driver: AsyncDriver = Depends(Provide[Container.neo4j_db.driver]),
) -> JSONResponse:
    """Cypher 쿼리를 실행하는 간단한 API"""
    start_time = time.time()
    
    try:
        logger.info(f"Executing Cypher query: {request.query}")
        
        # Neo4j 세션 생성 및 쿼리 실행
        async with neo4j_driver.session(default_access_mode=READ_ACCESS) as session:
            result = await session.run(request.query, parameters=request.parameters or {})
            
            # 결과 변환
            records = []
            async for record in result:
                record_dict = {}
                for key in record.keys():
                    record_dict[key] = convert_neo4j_value(record[key])
                records.append(record_dict)
        
        execution_time = (time.time() - start_time) * 1000
        
        response = CypherResponse(
            success=True,
            data=records,
            message="Query executed successfully",
            query_time_ms=execution_time,
            record_count=len(records)
        )
        
        return JSONResponse(content=response.model_dump())
        
    except Neo4jError as e:
        error_response = CypherResponse(
            success=False,
            data=[],
            message=f"Neo4j error: {str(e)}",
            query_time_ms=(time.time() - start_time) * 1000,
            record_count=0
        )
        return JSONResponse(content=error_response.model_dump(), status_code=400)
        
    except Exception as e:
        logger.error(f"Cypher query error: {str(e)}", exc_info=True)
        error_response = CypherResponse(
            success=False,
            data=[],
            message=f"Server error: {str(e)}",
            query_time_ms=(time.time() - start_time) * 1000,
            record_count=0
        )
        return JSONResponse(content=error_response.model_dump(), status_code=500)


@router.get(
    "/v1/cypher/health",
    summary="Cypher API 헬스체크"
)
@inject
async def cypher_health_check(
    neo4j_driver: AsyncDriver = Depends(Provide[Container.neo4j_db.driver]),
) -> JSONResponse:
    """Neo4j 연결 상태 확인"""
    try:
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 1 as test")
            record = await result.single()
            
            return JSONResponse(content={
                "status": "healthy",
                "message": "Neo4j connection is working",
                "test_result": record["test"]
            })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={"status": "unhealthy", "message": str(e)},
            status_code=503
        )
