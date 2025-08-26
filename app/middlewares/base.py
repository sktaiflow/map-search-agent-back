import time

from datetime import datetime
from enum import Enum
from fastapi import Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from uuid import uuid4
from contextvars import ContextVar
import json
from utils.logger import logger
from utils.timezone import KST

__ctx_request_context: ContextVar[Request] = ContextVar("ctx-request-context", default=None)

MONITORING_EXCLUDED_PATHS = ["/api/healthcheck/", "/api/healthcheck"]


class ErrorCode(Enum):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.code = self.name
        self.status_code = status_code


class BasicErrorCode(ErrorCode):
    BAD_REQUEST = ("Invalid request", 400)
    VALIDATION_ERROR = ("Validation error", 400)
    NOT_FOUND = ("Resource not found", 404)
    CONFLICT = ("Resource conflict", 409)
    METHOD_NOT_ALLOWED = ("Method not allowed", 405)
    SERVER_ERROR = ("Internal server error", 500)


class ErrorResponse(JSONResponse):
    def __init__(
        self, message: str = "", code: str = "Internal Server Error", status: int = 500, **kwargs
    ):
        body = {"code": code, "message": message, **kwargs}
        super().__init__(status_code=status, content=body)


async def common_middleware(request: Request, call_next):
    token = __ctx_request_context.set(request)

    request.state.start = time.time()
    request.state.request_id = (
        request.headers.get("x-request-id")
        or request.headers.get("x-transaction-id")
        or str(uuid4())
    )

    try:
        if request.url.path in MONITORING_EXCLUDED_PATHS:
            return await call_next(request)

        # current_span = tracer.current_span()
        # if current_span:
        #     current_span.set_tag(
        #         "langfuse_parent_span_id", request.headers.get("X-Langfuse-Parent-Span-Id", "")
        #     )
        #     current_span.set_tag(
        #         "langfuse_trace_id", request.headers.get("X-Langfuse-Trace-Id", "")
        #     )
        #     current_span.set_tag("request_id", request.state.request_id)

        response: Response = await call_next(request)
        process_time = (time.time() - request.state.start) * 1000
        response.headers["X-Process-Time"] = str(process_time)
    except Exception as e:
        # if current_span:
        #     current_span.set_tag("memory.error", True)
        #     current_span.set_tag("memory.error_message", str(e))
        raise
    finally:
        __ctx_request_context.reset(token)

    return response


async def request_response_handler(request: Request, call_next):
    try:
        request_body = json.loads(await request.body())
    except Exception:
        request_body = {}

    if request.url.path in MONITORING_EXCLUDED_PATHS:
        return await call_next(request)

    dt = datetime.fromtimestamp(request.state.start, KST).isoformat("T")

    logger.info(
        msg="",
        extra={
            "type": "request",
            "langfuse_span_id": request.headers.get("X-Langfuse-Parent-Span-Id", ""),
            "langfuse_trace_id": request.headers.get("X-Langfuse-Trace-Id", ""),
            "request_id": request.state.request_id,
            "method": request.method,
            "url": request.url,
            "datetime": dt,
            "body": request_body,
        },
    )

    response: Response = await call_next(request)

    request.state.process_time = (time.time() - request.state.start) * 1000
    response_body = getattr(request.state, "response_log", None) or "-"

    logger.info(
        msg="",
        extra={
            "type": "response",
            "request_id": request.state.request_id,
            "status": response.status_code,
            "latency": request.state.process_time,
            "body": response_body,
        },
    )
    return response


def _request_validation_error_to_message(exc: RequestValidationError):
    error = exc.errors()[-1]
    loc = ".".join([str(v) for v in error["loc"]])
    return f"{error['msg']} ({loc})"


async def error_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        message = exc.detail
    elif isinstance(exc, RequestValidationError):
        status_code = 400
        message = _request_validation_error_to_message(exc)
    else:
        logger.error(
            msg="",
            exc_info=exc,
            extra={
                "type": "internal-server-error",
                "request_id": request.state.request_id,
            },
        )
        status_code = 500
        message = "Internal Server Error"

    request.state.response_log = {
        "message": message,
    }

    return JSONResponse(status_code=status_code, content={"message": message})


def get_request_context() -> Request:
    return __ctx_request_context.get()
