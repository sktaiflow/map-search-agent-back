import asyncio
from typing import Literal, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from dependency_injector.wiring import Provide, inject

# from ddtrace import tracer  # Optional: enable if tracer is used

from app.container import Container
from app.agents import MapSearchAgent
from app.schemas.api.schema import InvokeRequest, InvokeResponse

####
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app import logger
from utils.request_handler import get_request_id

###

from langchain_core.runnables import RunnableConfig
from app.graph.configuration import Configuration

router = APIRouter(tags=["Map search Agent"])


@router.post(
    "/v1/invoke",
    response_model=InvokeResponse,
)
@inject
async def invoke_agent(
    input_data: InvokeRequest,
    agent: MapSearchAgent = Depends(Provide[Container.agents.map_agent]),
) -> JSONResponse:

    preprocess_input = (
        " ".join(input_data.query) if isinstance(input_data.query, list) else input_data.query
    )

    graph_input_data = {
        "user_id": input_data.user_id,
        "query": input_data.query,
        "query_synonym": preprocess_input,
        "expand_search": input_data.expand_search,
        "return_type": input_data.return_type,
        "user_info": input_data.user_info,
        "stream": False,
    }

    runnable_config = RunnableConfig(
        run_id=get_request_id(),
    )

    runnable_config = RunnableConfig()
    agent_response = await agent.ainvoke(
        input_data=InvokeRequest.model_validate(graph_input_data), runnable_config=runnable_config
    )

    print("#######")
    print(agent_response)
    print("#######")
    # TODO: postprocess_messages 처리
    return JSONResponse(content=agent_response.model_dump())
