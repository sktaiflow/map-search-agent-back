"""
Cypher API 라우터
이 파일은 Cypher 쿼리 실행을 위한 간단한 REST API 엔드포인트를 정의합니다.
"""

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from dependency_injector.wiring import Provide, inject
from neo4j.exceptions import Neo4jError
from app.models.graphmodel.graph import AsyncGraphModel
from app.database.neo4j import Neo4jDatabase
from app.container import Container
from app import logger
from configs import config as global_config

## test
from app.schemas.cypher import CypherRequest, CypherResponse


# API 라우터 생성
router = APIRouter(tags=["Cypher Query"])


@router.post(
    "/v1/cypher/execute",
    response_model=CypherResponse,
    summary="Cypher 쿼리 실행",
    description="Neo4j 데이터베이스에서 Cypher 쿼리를 실행합니다.",
    include_in_schema=global_config.stack_type not in ["prd", "stg"],
)
@inject
async def execute_cypher_query(
    request: CypherRequest,
    neo4j_engine: Neo4jDatabase = Depends(Provide[Container.neo4j_db.neo4j_db_engine]),
    neo4j_model: AsyncGraphModel = Depends(Provide[Container.neo4j_db.neo4j_model]),
) -> JSONResponse:
    """Cypher 쿼리를 실행하는 간단한 API"""
    try:
        logger.info(f"Executing Cypher query: {request.query}")

        # Neo4j 세션 생성 및 쿼리 실행
        async with neo4j_engine.get_async_session(mode="r") as session:
            result = await neo4j_model.query_database(
                query=request.query,
                params=request.params or {},
            )

        response = CypherResponse(
            data=result,
            message="OK",
            record_count=len(result),
        )

        return JSONResponse(content=response.model_dump(), status_code=200)

    except Neo4jError as e:
        error_response = CypherResponse(data=[], message=f"{str(e)}", record_count=0)
        return JSONResponse(content=error_response.model_dump(), status_code=400)

    except Exception as e:
        logger.error(f"Cypher query error: {str(e)}", exc_info=True)
        error_response = CypherResponse(
            data=[], message=f"Server error: {str(e)}", record_count=0
        )
        return JSONResponse(content=error_response.model_dump(), status_code=500)
