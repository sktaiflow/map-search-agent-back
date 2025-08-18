from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Literal, Tuple, Union
from datetime import datetime
from zoneinfo import ZoneInfo

SERVER_TIMEZONE = "Asia/Seoul"
KST = ZoneInfo(SERVER_TIMEZONE)
UTC = datetime.timezone.utc
now = datetime.datetime.now(KST)


class PlanStep(BaseModel):
    step: int
    tool: str
    reason: str


class PastStep(BaseModel):
    task: str
    tool: str
    query: Dict[str, Any]
    result: Any
    result_metadata: Dict[str, Any]


class AgentState(BaseModel):

    # default data
    current_date: Optional[datetime] = Field(default=now())
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
