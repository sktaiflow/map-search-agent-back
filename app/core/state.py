from typing import Annotated, Any, Dict, List, Optional

from langgraph.graph.message import add_messages, AnyMessage
from pydantic import BaseModel, Field, ConfigDict


class InputState(BaseModel):
    query: List[str] = Field(..., min_length=1, description="사용자 입력")
    is_reasoning: bool = Field(default=False, description="추론 여부")
    # conversation: List[Dict[str, Any]] = Field(default=[])
    setting_date: Optional[str] = ""
    stream: Optional[bool] = Field(default=False)
    model_config = ConfigDict(arbitrary_types_allowed=True)


class OutputState(BaseModel):
    raw_data: List[str] = Field(..., description="원시 데이터")
    summary: str = Field(..., min_length=1, description="요약 정보")
    insights: str = Field(..., min_length=1, description="인사이트")
    reasoning: str = Field(..., min_length=1, description="추론 과정")
    version: str = "map-search-agent-dev"


class RetryBudget(BaseModel):
    retry_count: int = 0
    max_retries: int = 3


class UsageBudget(BaseModel):
    time_used_ms: int = 0
    time_budget_ms: int = 3000  # (3초)


class BestSoFar(BaseModel):
    score: float = -1.0
    output: Optional[Dict[str, Any]] = None  # 최선 출력(당신 구조에 맞게 Any/str 등)
    reason: Optional[str] = None
    plan_snapshot: Optional[Dict[str, Any]] = None


class EvalStatus(BaseModel):
    accepted: bool = False
    score: float = -1.0
    detail: Dict[str, Any] = Field(default_factory=dict)  # 규칙별 점수/사유


class LoopTelemetry(BaseModel):
    failure_mode_hist: Dict[str, int] = Field(
        default_factory=dict
    )  # "schema","tool","timeout"... 카운트
    last_error: Optional[str] = None


class PrivateStateModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    is_reasoning: bool = Field(default=False, description="추론 여부")
    parsed: Optional[Dict] = None
    plan: List[str] = Field(default_factory=list)
    search_result: List[Dict] = Field(default_factory=list)
    trace: List[str] = Field(default_factory=list)
    tool_latency_ms: Optional[int] = None
    retry: RetryBudget = Field(default_factory=RetryBudget)
    usage: UsageBudget = Field(default_factory=UsageBudget)
    best_so_far: BestSoFar = Field(default_factory=BestSoFar)
    eval_status: EvalStatus = Field(default_factory=EvalStatus)
    loop_telemetry: LoopTelemetry = Field(default_factory=LoopTelemetry)


class OverallState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    query: list[str] = Field(default=[])
    # conversation: List[Dict[str, Any]] = Field(default=[])
    setting_date: Optional[str] = ""
    stream: Optional[bool] = Field(default=False)
    raw_data: List[str] = Field(default=[])
    summary: str = Field(default="")
    insights: str = Field(default="")
    reasoning: str = Field(default="")

    messages: Annotated[List[AnyMessage], add_messages] = Field(default_factory=list)
    private: PrivateStateModel = Field(default_factory=PrivateStateModel)
