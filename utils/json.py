"""JSON utility module using orjson for fast serialization"""

import orjson
from typing import Any


def dumps(obj: Any, default=None) -> str:
    """
    Serialize object to JSON string using orjson.
    
    Args:
        obj: Object to serialize
        default: Default function for objects that can't be serialized
        
    Returns:
        JSON string
    """
    return orjson.dumps(obj, default=default).decode('utf-8')


def loads(s: str) -> Any:
    """
    Deserialize JSON string to Python object using orjson.
    
    Args:
        s: JSON string to deserialize
        
    Returns:
        Deserialized Python object
    """
    return orjson.loads(s)