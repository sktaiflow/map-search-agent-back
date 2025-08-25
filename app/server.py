from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette.middleware.base import BaseHTTPMiddleware
from langfuse.decorators import langfuse_context

from app import api
from app.middlewares.base import (
    common_middleware,
    request_response_handler,
    error_handler,
)

from app import logger
from ddtrace.trace import tracer
from ddtrace.trace import TraceFilter

from app.container import Container
from configs import config
from configs import StackType, PHASE


KST = ZoneInfo("Asia/Seoul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.container = Container()
        await app.container.init_resources()
        app.state.ready = True
    except Exception as e:
        logger.error(f"Error during app startup: {e}", exc_info=True)
    yield
    try:
        app.state.ready = False
        await app.container.shutdown_resources()
    except Exception as e:
        print(f"Error during app shutdown: {e}")


async def healthcheck(request: Request):
    if not getattr(request.app.state, "ready", False):
        return Response(status_code=503, media_type="text/plain", content="NOT READY")
    return Response(media_type="text/plain", content="OK")


app = FastAPI(
    title="Map Search Agent API",
    version=config.app_version,
    description=config.api_description,
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_api_route(path="/api/healthcheck", endpoint=healthcheck)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(middleware_class=BaseHTTPMiddleware, dispatch=request_response_handler)
app.add_middleware(middleware_class=BaseHTTPMiddleware, dispatch=common_middleware)
app.add_exception_handler(Exception, error_handler)
app.add_exception_handler(RequestValidationError, error_handler)
app.add_exception_handler(HTTPException, error_handler)

app.include_router(api.agents.router)
