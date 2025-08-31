from typing import Annotated, Any, Dict, List, Optional

from langgraph.graph.message import add_messages, AnyMessage
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from typing import TypedDict
from typing import NotRequired


class InputState(BaseModel):
    user_id: str = Field(..., description="유저의 서비스 관리번호 또는 유저ID")
    query: List[str] = Field(..., description="사용자 발화")
    query_synonym: str = Field(..., description="동의어 변환 후 쿼리")
    expand_search: bool = Field(
        description="case_1: 정확 일치만, case_2: 확장 검색 허용",
        default=True,
    )
    return_type: Optional[int] = Field(
        description="0: neo4j schema 검색결과, 1: product id list만", 
        default=0
    )
    user_info: bool = Field(description="user 정보 조회 tool 사용 여부", default=True)

    setting_date: Optional[str] = ""
    stream: Optional[bool] = Field(default=False)
    model_config = ConfigDict(arbitrary_types_allowed=True)


class OutputState(BaseModel):
    plan: List[Dict[str, Any]] = Field(..., description="플랜")
    raw_data: Dict[str, Any] = Field(..., description="원시 데이터")
    summary: str = Field(..., min_length=1, description="요약 정보")
    insights: str = Field(..., min_length=1, description="인사이트")
    reasoning: str = Field(..., min_length=1, description="추론 과정")
    updated_at: datetime = Field(..., description="업데이트 시간")
    version: str = "map-search-agent-dev"
    fewshot_examples: List[Dict[str, Any]] = Field(default_factory=list)


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
    plan: List[Dict[str, Any]] = Field(default_factory=list)
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
    user_id: str = Field(default="")
    query: list[str] = Field(default=[])
    query_synonym: str = Field(default="")
    query_embedding: Optional[List[List[float]]] = Field(default=[])
    expand_search: bool = Field(default=True, description="case_1: 정확 일치, case_2: 확장 검색")
    return_type: int = Field(default=0, description="0: 전체 응답, 1: product_id만")
    user_info: bool = Field(default=True, description="user 정보 조회 여부")
    setting_date: Optional[str] = ""
    stream: Optional[bool] = Field(default=False)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    summary: str = Field(default="")
    insights: str = Field(default="")
    reasoning: str = Field(default="")
    product_meta: List[Dict[str, Any]] = Field(default_factory=list)
    user_info_data: List[Dict[str, Any]] = Field(default_factory=list)
    fewshot_examples: List[Dict[str, Any]] = Field(default_factory=list)
    messages: Annotated[List[AnyMessage], add_messages] = Field(default_factory=list)
    private: PrivateStateModel = Field(default_factory=PrivateStateModel)
