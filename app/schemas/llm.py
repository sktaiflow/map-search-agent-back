from typing import Literal, List, Dict, Any, Optional
from pydantic import BaseModel


class ToolCall(BaseModel):
    id: Optional[str] = None
    name: str
    args: Dict[str, Any] = {}


class LLMMetadata(BaseModel):
    id: Optional[str] = None
    response: Dict[str, Any] = {}
    usage: Dict[str, Any] = {}


class LLMOutput(BaseModel):
    type: Literal["text", "tool"]
    content: str = ""
    tool_calls: List[ToolCall] = []
    metadata: LLMMetadata = LLMMetadata()
