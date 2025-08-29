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
from configs.default import BaseConfig

# 환경 설정 로드
config = BaseConfig()

# API 라우터 생성
router = APIRouter(tags=["Cypher Query"])


@router.post(
    "/v1/cypher/execute",
    response_model=CypherResponse,
    summary="Cypher 쿼리 실행",
    description="Neo4j 데이터베이스에서 Cypher 쿼리를 실행합니다.",
    include_in_schema=config.stack_type not in ["prd", "stg"]
)
@inject
async def execute_cypher_query(
    request: CypherRequest,
    neo4j_driver: AsyncDriver = Depends(Provide[Container.neo4j_db.driver]),
) -> JSONResponse:
    """Cypher 쿼리를 실행하는 간단한 API"""    
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
                    record_dict[key] = record[key]
                records.append(record_dict)
                
        response = CypherResponse(
            success=True,
            data=records,
            message="Query executed successfully",
            record_count=len(records)
        )
        
        return JSONResponse(content=response.model_dump())
        
    except Neo4jError as e:
        error_response = CypherResponse(
            success=False,
            data=[],
            message=f"Neo4j error: {str(e)}",
            record_count=0
        )
        return JSONResponse(content=error_response.model_dump(), status_code=400)
        
    except Exception as e:
        logger.error(f"Cypher query error: {str(e)}", exc_info=True)
        error_response = CypherResponse(
            success=False,
            data=[],
            message=f"Server error: {str(e)}",
            record_count=0
        )
        return JSONResponse(content=error_response.model_dump(), status_code=500)

