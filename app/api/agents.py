import asyncio
from typing import Literal, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from dependency_injector.wiring import Provide, inject

# from ddtrace import tracer  # Optional: enable if tracer is used

from app.container import Container
from app.agents.base import BaseAgent
from app.schemas.api.schema import InvokeRequest, InvokeResponse

####
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app import logger

###

from langchain_core.runnables import RunnableConfig

router = APIRouter(tags=["Map search Agent"])


# TODO: temp 함수, 구현 완료시 없애기
async def apreprocess_input_mock(input_data: InvokeRequest):
    return input_data.query


@router.post(
    "/v1/invoke",
    response_model=InvokeResponse,
)
@inject
async def invoke_agent(
    input_data: InvokeRequest,
    agent: BaseAgent = Depends(Provide[Container.agents.map_agent]),
) -> JSONResponse:

    # 쿼리 전처리 - List[str] -> str 변환
    preprocess_input = " ".join(input_data.query) if isinstance(input_data.query, list) else input_data.query

    logger.info(f"preprocess_input: {preprocess_input}")

    graph_input_data = {
        "user_id": input_data.user_id,
        "query": input_data.query,
        "query_synonym": preprocess_input,
        "expand_search": input_data.expand_search,
        "return_type": input_data.return_type,
        "user_info": input_data.user_info,
        "stream": False,
    }

    # runnable_config 설정
    from configs import config as global_config
    from app.graph.configuration import Configuration
    default_cfg = Configuration()
    runnable_config = RunnableConfig(configurable={
        "llm_model": global_config.llm_model,
        "temperature": global_config.llm_temperature,
        "seed": global_config.llm_seed,
        "streaming": graph_input_data["stream"]
    })
    graph_result = await agent.ainvoke(input_data=graph_input_data, runnable_config=runnable_config)
    
    # return_type에 따른 응답 분기
    if input_data.return_type == 1:
        # return_type=1: product_id만 반환 (LLM 호출 최소화)
        response_data = {
            "raw_result": graph_result.get("raw_data", {}),
            "product_meta": graph_result.get("product_meta", []),  # 이미 ID 리스트로 처리됨
            "user_info": graph_result.get("user_info_data", [])
        }
    else:
        # return_type=0: 전체 응답 (insights, summary, reasoning 포함)
        response_data = {
            "insights": graph_result.get("insights", ""),
            "summary": graph_result.get("summary", ""),
            "reasoning": graph_result.get("reasoning", ""),
            "raw_result": graph_result.get("raw_data", {}),
            "product_meta": graph_result.get("product_meta", []),
            "user_info": graph_result.get("user_info_data", []),
            "updated_at": graph_result.get("updated_at", "")
        }
    
    response = InvokeResponse(code=200, data=response_data)
    
    logger.info(f"Response type: {input_data.return_type}, Data keys: {list(response_data.keys())}")
    return JSONResponse(content=response.model_dump())
