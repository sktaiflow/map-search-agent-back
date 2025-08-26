import orjson

from typing import Any, Callable, Optional


def dumps(data, default: Optional[Callable[[Any], Any]] = ...) -> str:
    return orjson.dumps(data, default).decode()


def loads(data) -> dict[str, Any] | list:
    return orjson.loads(data)


JSONEncodeError = orjson.JSONEncodeError
JSONDecodeError = orjson.JSONDecodeError
