import logging

from types import TracebackType
from typing import Optional, Tuple, Union

from utils.logger import logger
from app.middlewares.base import get_request_context


_SysExcInfoType = Union[
    Tuple[type, BaseException, Optional[TracebackType]], Tuple[None, None, None]
]
_ExcInfoType = Union[None, bool, _SysExcInfoType, BaseException]
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def _log(
    level: int,
    message: str,
    exc_info: _ExcInfoType = None,
    stack_info: bool = False,
    stacklevel: int = 1,
    **extra,
):
    if "request_id" not in extra:
        request = get_request_context()
        extra["request_id"] = request.state.request_id if request else "-"
    logger.log(
        level, message, exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra
    )


def info(
    message: str = "",
    exc_info: _ExcInfoType = None,
    stack_info: bool = False,
    stacklevel: int = 1,
    **extra,
) -> None:
    _log(logging.INFO, message, exc_info, stack_info, stacklevel, **extra)


def warn(
    message: str = "",
    exc_info: _ExcInfoType = None,
    stack_info: bool = False,
    stacklevel: int = 1,
    **extra,
) -> None:
    _log(logging.WARN, message, exc_info, stack_info, stacklevel, **extra)


def error(
    message: str = "",
    exc_info: _ExcInfoType = None,
    stack_info: bool = False,
    stacklevel: int = 1,
    **extra,
) -> None:
    _log(logging.ERROR, message, exc_info, stack_info, stacklevel, **extra)


def exception(
    message: str = "",
    exc_info: _ExcInfoType = True,
    stack_info: bool = True,
    stacklevel: int = 1,
    **extra,
) -> None:
    _log(logging.ERROR, message, exc_info, stack_info, stacklevel, **extra)


def event(message: str = "", **extra):
    extra["type"] = "event"
    _log(logging.INFO, message, **extra)


def breadcrumb(
    message: str = "",
    level: int = logging.WARN,
    exc_info: _ExcInfoType = None,
    stack_info: bool = False,
    stacklevel: int = 1,
    **extra,
) -> None:
    extra["type"] = "breadcrumb"
    _log(level, message, exc_info, stack_info, stacklevel, **extra)
