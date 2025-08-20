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
