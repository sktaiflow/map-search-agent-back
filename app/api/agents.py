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

    # preprocess_input = await agent.apreprocess_input(input_data, request_params={})

    preprocess_input = await agent.apreprocess_input_mock(input_data)

    logger.info(f"preprocess_input: {preprocess_input}")

    graph_input_data = {
        "user_id": input_data.user_id,
        "query": input_data.query,
        "query_synonym": preprocess_input,
        "search_type": input_data.search_type,
        "return_type": input_data.return_type,
        "transaction_id": "",
        "user_info_yn": input_data.user_info_yn,
        "stream": False,
    }

    # TODO: runnable_config 에 대한 처리 필요
    runnable_config = RunnableConfig()
    response = InvokeResponse(
        code=200,
        data=dict(
            await agent.ainvoke(input_data=graph_input_data, runnable_config=runnable_config)
        ),
    )
    print("#######")
    print(response)
    print("#######")
    # TODO: postprocess_messages 처리
    return JSONResponse(content=response.model_dump())
