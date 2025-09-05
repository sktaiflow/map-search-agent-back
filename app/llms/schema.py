from typing import Any, Dict, List, Optional, Union
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class ToolCall(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    function: Optional[Dict[str, Any]] = None


class LLMMetadata(BaseModel):
    id: Optional[str] = None
    response: Dict[str, Any] = {}
    usage: Dict[str, Any] = {}


class LLMOutput(BaseModel):
    type: str
    content: Any
    tool_calls: List[ToolCall] = []
    metadata: LLMMetadata = LLMMetadata()
