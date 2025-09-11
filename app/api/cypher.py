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
from neo4j.graph import Node as Neo4jNode, Relationship as Neo4jRelationship, Path as Neo4jPath
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
            # 방법 2 에 대한 node parsing 예제 코드 -> 실제 코드는 agent의 postprocess로 실제로 들어가야함
            def _sanitize_value(value: Any) -> Any:
                # Fast-path primitives
                if value is None or isinstance(value, (str, int, float, bool)):
                    return value

                # Datetime-like
                try:
                    from datetime import date, datetime

                    if isinstance(value, (date, datetime)):
                        return value.isoformat()
                except Exception:
                    pass

                # Bytes
                if isinstance(value, (bytes, bytearray)):
                    try:
                        return value.decode("utf-8", errors="replace")
                    except Exception:
                        return repr(value)

                # Neo4j Node
                if isinstance(value, Neo4jNode):
                    element_id = getattr(value, "element_id", None)
                    node_id = element_id if element_id is not None else getattr(value, "id", None)
                    labels = list(getattr(value, "labels", []) or [])
                    props = {k: _sanitize_value(value.get(k)) for k in value.keys()}
                    return {"id": node_id, "labels": labels, "properties": props}

                # Neo4j Relationship
                if isinstance(value, Neo4jRelationship):
                    element_id = getattr(value, "element_id", None)
                    rel_id = element_id if element_id is not None else getattr(value, "id", None)
                    rel_type = getattr(value, "type", None)
                    start_id = getattr(value, "start_node_element_id", None)
                    if start_id is None:
                        start_id = getattr(value, "start_node_id", None)
                    end_id = getattr(value, "end_node_element_id", None)
                    if end_id is None:
                        end_id = getattr(value, "end_node_id", None)
                    props = {k: _sanitize_value(value.get(k)) for k in value.keys()}
                    return {
                        "id": rel_id,
                        "type": rel_type,
                        "start": start_id,
                        "end": end_id,
                        "properties": props,
                    }

                # Neo4j Path
                if isinstance(value, Neo4jPath):
                    nodes = [_sanitize_value(n) for n in getattr(value, "nodes", [])]
                    rels = [_sanitize_value(r) for r in getattr(value, "relationships", [])]
                    return {"nodes": nodes, "relationships": rels}

                # Mapping
                if isinstance(value, dict):
                    return {k: _sanitize_value(v) for k, v in value.items()}

                # Iterables
                if isinstance(value, (list, tuple, set)):
                    return [_sanitize_value(v) for v in value]

                # Fallback representation
                return repr(value)

            records: List[Dict[str, Any]] = []
            for record in result:
                sanitized = {k: _sanitize_value(v) for k, v in record.items()}
                records.append(sanitized)

        response = CypherResponse(
            data=records,
            message="OK",
            record_count=len(records),
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
