from typing import Annotated, List, Tuple, Optional, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class PlanExecuteState(TypedDict):
    input: str
    plan: List[str]
    past_steps: Optional[List[Tuple]]
    response: Optional[str]
    user_info: Optional[Dict[str, Any]]
    product_meta: Optional[Dict[str, Any]]
    messages: Annotated[list, add_messages]
    cypher: Optional[str]


class GraphState(TypedDict):
    error: Optional[str]
    input: str
    plan: List[str]
    past_steps: Optional[List[Tuple]]
    response: Optional[str]
    user_info: Optional[Dict[str, Any]]
    product_meta: Optional[Dict[str, Any]]
    messages: Annotated[list, add_messages]
    cypher: Optional[str]


class Plan(BaseModel):
    steps: List[str] = Field(description="Plan steps")


class Response(BaseModel):
    response: str
