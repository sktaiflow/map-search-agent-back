from typing import Annotated, Any, Dict, List, Optional

from langgraph.graph.message import add_messages, AnyMessage
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from typing import TypedDict
from typing import NotRequired


class InputState(BaseModel):
    user_id: str = Field(
        ..., description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)"
    )
    query: str = Field(..., description="그래프 입력")
    query_synonym: str = Field(..., description="동의어 변환 후 쿼리")
    expand_search: Optional[bool] = Field(
        description="검색 타입, True: 기본 검색, False: 확장 검색",
        default=True,
    )
    return_type: Optional[int] = Field(
        description="0: Neo4jSchema, 1: product_id List[str]", default=0
    )
    transaction_id: Optional[str] = Field(description="트랜잭션 아이디")
    user_info_yn: Optional[bool] = Field(
        description="사용자 정보 포함 여부", default=True
    )

    setting_date: Optional[str] = ""
    stream: Optional[bool] = Field(default=False)
    model_config = ConfigDict(arbitrary_types_allowed=True)


class OutputState(BaseModel):
    insights: Optional[str] = Field(..., min_length=1, description="인사이트")
    summary: Optional[str] = Field(..., min_length=1, description="요약 정보")
    reasoning: Optional[str] = Field(..., min_length=1, description="추론 과정")
    updated_at: Optional[datetime] = Field(..., description="업데이트 시간")
    raw_result: Dict[str, Any] = Field(..., description="원시 데이터")
    return_type: Optional[int] = Field(
        description="0: Neo4jSchema, 1: product_id List[str]", default=0
    )


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


# TODO: 아래의 각 파라미터가 하는 역할 명확히 하기
class PrivateStateModel(BaseModel):
    # 확실히 필요한 것들
    plan: List[Dict[str, Any]] = Field(
        default_factory=list, description="도구 호출 순서"
    )
    # search_result는 plan 내에 포함
    # search_result: List[Dict] = Field(default_factory=list)
    trace: List[str] = Field(default_factory=list, description="디버깅용 트레이스 로그")
    retry: RetryBudget = Field(default_factory=RetryBudget)
    usage: UsageBudget = Field(default_factory=UsageBudget)
    eval_status: EvalStatus = Field(default_factory=EvalStatus)
    # 용도 확인 필요한 것들
    model_config = ConfigDict(arbitrary_types_allowed=True)
    is_reasoning: bool = Field(default=False, description="추론 여부")
    parsed: Optional[Dict] = None
    tool_latency_ms: Optional[int] = None
    best_so_far: BestSoFar = Field(default_factory=BestSoFar)
    loop_telemetry: LoopTelemetry = Field(default_factory=LoopTelemetry)
    next_action_after_replan: Optional[str] = Field(
        default=None, description="replan 이후 이동할 다음 단계"
    )


# TODO: 아래의 각 파라미터가 하는 역할 명확히 하기
class OverallState(BaseModel):
    # 확실히 필요한 것들
    user_id: str = Field(default="")
    query: list[str] = Field(default=[])
    query_synonym: str = Field(default="")
    return_type: int = Field(
        default=0,
        description="0: 상세 결과 반환, 1: product_id List[str]",
    )
    expand_search: bool = Field(
        default=True,
        description="검색 타입, True: 기본 검색, False: 확장 검색",
    )
    private: PrivateStateModel = Field(default_factory=PrivateStateModel)
    # 용도 확인 필요한 것들
    model_config = ConfigDict(arbitrary_types_allowed=True)
    query_embedding: Optional[List[List[float]]] = Field(default=[])
    setting_date: Optional[str] = ""
    stream: Optional[bool] = Field(default=False)
    raw_data: List[str] = Field(default=[])
    fewshot_examples: List[Dict[str, Any]] = Field(default_factory=list)
    messages: Annotated[List[AnyMessage], add_messages] = Field(default_factory=list)
    # 최종 결과 관련 필드인데 여기에서 꼭 필요한지 검토
    summary: str = Field(default="")
    insights: str = Field(default="")
