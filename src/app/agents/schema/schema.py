from typing import Annotated, Any, Dict, List, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class PlanStep(TypedDict):
    step: int
    tool: str
    reason: str


class PastStep(TypedDict):
    task: str
    tool: str
    query: Dict[str, Any]
    result: Any
    result_metadata: Dict[str, Any]


class AgentState(TypedDict):
    input: str
    plan: List[PlanStep]
    past_steps: List[PastStep]
    response: Optional[Dict[str, Any]]  # 3단계 구조: {raw_data, summary, insights}
    reasoning: Optional[str]
    raw_results: Optional[Dict[str, Any]]
    user_info: Optional[Dict[str, Any]]
    product_meta: Optional[Dict[str, Any]]
    messages: Annotated[list, add_messages]
    cypher: Optional[str]
    step_index: Optional[int]
    retry_count: Optional[int]
    max_retries: Optional[int]