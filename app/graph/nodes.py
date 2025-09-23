from typing import Dict, Any, List, Iterable
import asyncio
import json
from datetime import datetime
from utils.logger import logger

from app.graph.states import OverallState, InputState
from app.graph.configuration import Configuration as Config
from app.core.prompts import (
    PLANNING_PROMPT,
    INSIGHTS_PROMPT,
    SUMMARY_PROMPT,
    REASONING_PROMPT,
    EVALUATION_PROMPT,
    REPLAN_FAILURE_PROMPT,
    REPLAN_SUCCESS_PROMPT,
    RESULT_PROMPT,
)
from app.graph.schema import Deps
from utils.timezone import KST
from langchain_core.runnables import RunnableConfig
from langchain.output_parsers import PydanticOutputParser
from app.graph.schema import Plan
from langchain_core.utils.function_calling import convert_to_openai_tool


def _make_serializable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _make_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_make_serializable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


# OpenAI 함수 호출 규격으로 툴 정보를 변환
def convert_to_openai_tools(tools: Any) -> List[Dict[str, Any]]:
    openai_tools: List[Dict[str, Any]] = []
    for tool in tools:
        tool_spec = convert_to_openai_tool(tool)
        description = getattr(tool, "description", None)
        if description and isinstance(tool_spec.get("function"), dict):
            tool_spec["function"].setdefault("description", description)
        openai_tools.append(tool_spec)
    return openai_tools


# # TODO: 동의어 키워드로 쪼개서 호출해서 처리하는 로직 필요
# async def mock_up_replace_query_with_synonym(query: str) -> str:
#     """동의어 처리"""
#     return query


# async def apreprocess_node(state: InputState, config: RunnableConfig) -> OverallState:
#     """초기 상태 설정, 동의어 처리해서 노드 초기화 진행"""

#     def convert_list_str(query: List[str]) -> str:
#         return " ".join(query)

#     query = convert_list_str(state.query)
#     ## 동의어 처리하는 부분
#     updated_query = await mock_up_replace_query_with_synonym(query=query)
#     return {"query_synonym": updated_query}


async def plan_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """쿼리를 브레이크다운하여 subtasks 생성"""
    cfg = Config.from_runnable_config(config)

    # 여러 개의 질문이 들어올 경우 하나의 문자열로 합쳐서 처리 -> 아직 동의어 관련 로직 미구현
    original_query = state.query
    if isinstance(original_query, list):
        query = " ".join(original_query)
    else:
        query = original_query

    # BaseTool 클래스에 바로 적용할 수 있는 LangChain의 convert_to_openai_tool 함수를 이용해서 액티브 툴의 명세를 생성
    # TODO: OpenAI tool 스펙을 캐싱해서 반복 생성 비용을 줄일 수 있을 듯
    active_tools = await deps.toolkit.all_active_tools()
    openai_tool_specs = convert_to_openai_tools(active_tools)

    # query = state.query_synonym
    trace = list(state.private.trace or [])

    # LLM 프롬프트 구성
    prompt = PLANNING_PROMPT.partial(
        user_id=state.user_id,
    )
    system_message = prompt.format()

    trace.append("계획 수립을 위한 LLM 호출을 시작합니다.")
    llm_response = await deps.llm_client.agenerate_response(
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": query},
        ],
        model=cfg.llm_model,
        temperature=0.0,
        max_tokens=2000,
        response_format={"type": "json_object"},
        seed=cfg.seed,
        tools=openai_tool_specs,
        tool_choice="auto",
    )

    first_tool = {}

    if llm_response.is_toolcall and llm_response.tool_calls:
        first_call = llm_response.tool_calls[0]
        if len(llm_response.tool_calls) > 1:
            trace.append("여러 개의 도구 호출이 감지되어 첫 번째 호출만 사용합니다.")
        first_tool = {
            "step": 1,
            "tool": first_call.name,
            "args": first_call.arguments,
            "executed": False,
            # 아래 두 개 꼭 필요한지 검토
            # "tool_call_id": first_call.id,
            # "raw_arguments": first_call.raw_arguments,
        }
        trace.append(
            f"도구 호출이 생성되었습니다: {first_call.name}: {first_call.arguments}"
        )
    else:
        trace.append("LLM이 호출할 도구를 찾지 못하였습니다.")

    private_dict = state.private.model_dump()
    private_dict.update(
        {
            "plan": [first_tool],
            "trace": trace,
        }
    )

    return {"private": private_dict}


# 실제 도구를 호출하는 노드
async def execute_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """
    앞 단계 (plan_node 또는 replan_node) 에서 선정된 도구를 호출하고, 결과를 리턴
    """
    plan = list(state.private.plan or [])
    trace = list(state.private.trace or [])

    # TODO: 액티브 툴 목록 캐싱 필요
    active_tools = await deps.toolkit.all_active_tools()

    # (1) 플랜이 없거나, (2) 가장 최근 플랜이 이미 실행된 플랜이거나, (3) 플랜에 툴 호출이 없는 경우에는 실패처리
    if (
        not plan
        or (isinstance(plan[-1], dict) and plan[-1].get("executed"))
        or (isinstance(plan[-1], dict) and not plan[-1].get("tool"))
    ):
        trace.append("실행할 계획이 없어 스킵합니다.")
        private_state = state.private.model_dump()
        private_state.update({"trace": trace})
        return {"private": private_state}

    # 가장 최근에 새로 생성된 플랜을 실행
    current_step = plan[-1]

    tool_result: Dict[str, Any] = current_step.get("tool_result", {})
    total_elapsed = state.private.tool_latency_ms or 0

    step_index = current_step.get("step")
    task_name = current_step.get("task", f"단계 {step_index}")
    tool_name = current_step.get("tool")
    query_params = current_step.get("args", current_step.get("query", {})) or {}
    # 아래 두 필드는 필요 없어보임
    # tool_call_id = current_step.get("tool_call_id")
    # raw_arguments = current_step.get("raw_arguments")

    trace.append(f"{step_index}단계 실행 시작: {task_name}")
    step_start = datetime.now()

    # tool_result 항목을 생성하기 위해 포메팅하는 함수
    def format_record_result(
        *,
        success: bool,
        result: Any = None,
        error: str | None = None,
        latency_ms: int = 0,
    ) -> Dict[str, Any]:
        result_dict = {
            # "step": step_index,
            # "task": task_name,
            # "tool": tool_name,
            # "tool_call_id": tool_call_id,
            # "query": query_params,
            # "raw_arguments": raw_arguments,
            "result": result,
            "success": success,
            "error": error,
            "execution_time_ms": latency_ms,
        }

        return result_dict

    # tool_name에 해당하는 도구를 active_tools에서 찾음
    tool_instance = next(
        (
            tool
            for tool in active_tools
            if getattr(tool, "name", None) == tool_name
            or tool.__class__.__name__ == tool_name
        ),
        None,
    )

    if not tool_instance:
        trace.append(f"{step_index}단계 실패: {tool_name} 도구를 찾지 못했습니다.")
        private_state = state.private.model_dump()
        private_state.update({"trace": trace})
        return {"private": private_state}

    trace.append(f"{step_index}단계에서 {tool_name} 실행: {query_params}")
    try:
        # 도구를 실제로 실행하는 부분
        result = await tool_instance.arun(query_params)

        latency = int((datetime.now() - step_start).total_seconds() * 1000)
        trace.append(f"{step_index}단계 성공 ({latency}ms)")
        tool_result = format_record_result(
            success=True, result=result, latency_ms=latency
        )
        total_elapsed += latency
    except Exception as error:
        latency = int((datetime.now() - step_start).total_seconds() * 1000)
        message = f"{tool_name} 실행 중 오류 발생: {error}"
        trace.append(f"{step_index}단계 실패: {message}")
        tool_result = format_record_result(
            success=False, error=str(error), latency_ms=latency
        )
        total_elapsed += latency

    # TODO: 여기서 plan을 이렇게 직접 건드리면 OverallState에 바로 변경내용이 반영되는데, 이렇게 해도 되는지 검토 필요
    plan[-1]["executed"] = True
    plan[-1]["tool_result"] = tool_result
    private_state = state.private.model_dump()
    private_state.update(
        {
            "plan": plan,
            "trace": trace,
            "tool_latency_ms": total_elapsed,
        }
    )

    return {"private": private_state}


async def evaluate_node(
    state: OverallState, deps: Deps, config: RunnableConfig
) -> dict:
    """execute_node 결과를 LLM으로 평가하고 상태를 갱신"""
    cfg = Config.from_runnable_config(config)
    trace = list(state.private.trace or [])
    plan = list(state.private.plan or [])

    # 플랜이 없거나, 실행되었으나 평가되지 않은 플랜이 없으면 스킵
    if not plan or (isinstance(plan[-1], dict) and plan[-1].get("evaluated")):
        trace.append(
            f"평가할 실행 결과가 없습니다. 가장 최근의 플랜은 이미 평가되었습니다."
        )
        private_state = state.private.model_dump()
        private_state.update({"trace": trace})
        return {"private": private_state}

    current_step = plan[-1]
    tool_result = current_step.get("tool_result", {})
    trace.append("실행 결과 평가를 시작합니다.")

    eval_status = {}

    # TODO: 질의 처리하는 코드가 다른 노드에도 중복으로 들어있어서 통합이 필요함
    if state.query_synonym:
        original_question = state.query_synonym
    elif isinstance(state.query, list):
        original_question = " ".join(state.query)
    else:
        original_question = state.query

    if not tool_result or (
        isinstance(tool_result, dict) and not tool_result.get("success", False)
    ):
        # 실행 결과 자체가 없거나 실행이 실패했다면 재계획이 필요하므로 실패로 간주
        eval_status = {
            "evaluated": True,
            "accepted": False,
            "score": 0.0,
            # TODO: detail에 어떤 정보를 담을지 검토
            "evaluation_detail": {
                "score": 0.0,
                "reason": "no_results",
                "eval_message": "평가할 실행 결과가 없습니다.",
            },
        }
        trace.append("평가 대상이 없어 재계획이 필요합니다.")
    else:
        steps_payload: Dict[str, Any] = {}
        tool_name = current_step.get("tool", "")
        # 툴 질의
        tool_query = current_step.get("args", {}).get("query", "")
        # 툴 선택 이유
        tool_reason = current_step.get("args", {}).get("tool_select_reason", "")
        # 툴 실행 결과로 리턴받은 데이터
        tool_result_data = tool_result.get("result", {}).get("data", [])

        steps_payload = {
            "tool_name": tool_name,
            "tool_select_reason": tool_reason,
            "tool_query": tool_query,
            "tool_select_reason": tool_reason,
            "tool_result_data": tool_result_data,
            # "error": current_step.get("error", ""),
            # "previous_success": bool(result.get("success")),
        }

        prompt_message = EVALUATION_PROMPT.format(
            original_question=original_question,
            retry_count=state.private.retry.retry_count,
            max_retries=state.private.retry.max_retries,
            steps_json=json.dumps(steps_payload, ensure_ascii=False),
        )

        try:
            llm_response = await deps.llm_client.agenerate_response(
                messages=[{"role": "system", "content": prompt_message}],
                model=cfg.llm_model,
                temperature=0.0,
                max_tokens=700,
                response_format={"type": "json_object"},
                seed=cfg.seed,
            )

            payload = json.loads(llm_response.message or "{}")
            accepted = bool(payload.get("accepted", False))
            score = float(payload.get("score", 0.0))
            detail = payload.get("detail") or {}

            eval_status["evaluated"] = True
            eval_status["accepted"] = accepted
            eval_status["evaluation_detail"] = {
                "score": score,
                "reason": detail.get("reason", ""),
                "eval_message": detail.get("message", ""),
            }

            trace.append(
                "LLM 평가 결과: "
                + ("성공" if accepted else "실패")
                + f" / 점수: {score:.2f}"
            )

        except Exception as error:
            # TODO: LLM 호출이나 응답 파싱에 실패한 경우엔 어떻게 할지 아직 미정
            trace.append(f"평가 단계에서 오류 발생: {error}")

    # Evaluation을 통과하지 못한 경우 한 번 더 시도해야함을 retry_budget에 반영
    retry_budget = state.private.retry.model_dump()
    if not eval_status.get("accepted", False):
        retry_budget["retry_count"] = retry_budget.get("retry_count", 0) + 1
        trace.append(
            f"재시도 횟수 {retry_budget['retry_count']}/{retry_budget.get('max_retries', 3)}"
        )

    current_step["evaluated"] = eval_status.get("evaluated", False)
    current_step["accepted"] = eval_status.get("accepted", False)
    current_step["evaluation"] = eval_status.get("evaluation_detail", {})
    plan[-1].update(current_step)

    private_state = state.private.model_dump()
    private_state.update(
        {
            "plan": plan,
            "retry": retry_budget,
            "trace": trace,
        }
    )

    return {"private": private_state}


async def replan_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """LLM 판단에 따라 다음 실행 단계를 설계"""
    cfg = Config.from_runnable_config(config)
    trace = list(state.private.trace or [])
    plans = list(state.private.plan or [])
    current_step = plans[-1] if plans else {}

    # 최근 스텝이 실패한 경우 -> 원본 질문, args, tool_result, accepted, evaluation를 보내서 도구 재선택 또는 리프레이즈
    # 최근 스텝이 성공한 경우 -> 원본 질문, args, tool_result, accepted, evaluation를 보내서 다음 단계 도구 선택

    # TODO: 질의 처리하는 코드가 다른 노드에도 중복으로 들어있어서 통합이 필요함
    if state.query_synonym:
        original_question = state.query_synonym
    elif isinstance(state.query, list):
        original_question = " ".join(state.query)
    else:
        original_question = state.query

    last_args = current_step.get("args", {})
    last_tool_result = current_step.get("tool_result", {})
    last_accepted = current_step.get("accepted", False)
    last_evaluation = current_step.get("evaluation", {})

    trace.append(
        "재계획 단계를 시작합니다. 평가 결과: " + ("성공" if last_accepted else "실패")
    )

    retry_budget = state.private.retry
    if retry_budget.retry_count >= retry_budget.max_retries:
        trace.append(
            f"재시도 한도 {retry_budget.retry_count}/{retry_budget.max_retries}를 초과하여 재계획을 중단합니다."
        )
        private_state = state.private.model_dump()
        private_state.update(
            {
                "trace": trace,
                "next_action_after_replan": "output",
            }
        )
        return {"private": private_state}

    # 여기부터 아래 부분은 plan_node와 유사한 구조
    active_tools = await deps.toolkit.all_active_tools()
    openai_tool_specs = convert_to_openai_tools(active_tools)

    if not last_accepted:
        # 직전 단계 도구 호출 평가 탈락
        prompt_message = REPLAN_FAILURE_PROMPT.format(
            original_question=original_question,
            last_args=json.dumps(last_args, ensure_ascii=False),
            tool_result=json.dumps(last_tool_result, ensure_ascii=False),
            last_evaluation=json.dumps(last_evaluation, ensure_ascii=False),
        )
    else:
        # 직전 단계 도구 호출 평가 통과
        prompt_message = REPLAN_SUCCESS_PROMPT.format(
            original_question=original_question,
            all_plans=json.dumps(plans, ensure_ascii=False),
        )

    cfg_llm_kwargs = {
        "model": cfg.llm_model,
        "temperature": 0.0,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "seed": cfg.seed,
        "tools": openai_tool_specs,
        "tool_choice": "auto",
    }

    llm_response = await deps.llm_client.agenerate_response(
        messages=[{"role": "system", "content": prompt_message}],
        **cfg_llm_kwargs,
    )

    first_tool = {}

    if llm_response.is_toolcall and llm_response.tool_calls:
        first_call = llm_response.tool_calls[0]
        if len(llm_response.tool_calls) > 1:
            trace.append("여러 개의 도구 호출이 감지되어 첫 번째 호출만 사용합니다.")
        first_tool = {
            "step": 1,
            "tool": first_call.name,
            "args": first_call.arguments,
            "executed": False,
            # 아래 두 개 꼭 필요한지 검토
            # "tool_call_id": first_call.id,
            # "raw_arguments": first_call.raw_arguments,
        }
        trace.append(
            f"도구 호출이 생성되었습니다: {first_call.name}: {first_call.arguments}"
        )
        next_action = "execute"
    else:
        llm_msg = json.loads(llm_response.message).get("comment", "")
        trace.append(llm_msg)
        next_action = "output"

    private_state = state.private.model_dump()
    private_state.update(
        {
            "plan": plans + [first_tool] if first_tool else plans,
            "trace": trace,
            "next_action_after_replan": next_action,
        }
    )

    return {"private": private_state}


async def output_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """최종 결과물을 생성"""
    cfg = Config.from_runnable_config(config)
    now = datetime.now(KST)

    plans = list(state.private.plan or [])
    trace = list(state.private.trace or [])
    trace.append("최종 응답 생성을 시작합니다.")

    raw_result = {
        "plans": plans,
        "debug_trace": trace,
    }

    # TODO: 질의 처리하는 코드가 다른 노드에도 중복으로 들어있어서 통합이 필요함
    if state.query_synonym:
        original_question = state.query_synonym
    elif isinstance(state.query, list):
        original_question = " ".join(state.query)
    else:
        original_question = state.query

    # LLM으로 검색 결과를 정제하여 질문과 직접 관련된 항목만 남긴다.
    result_prompt = RESULT_PROMPT.format(
        user_query=original_question,
        plans=json.dumps(plans, ensure_ascii=False),
    )

    result_response = await deps.llm_client.agenerate_response(
        messages=[{"role": "system", "content": result_prompt}],
        model=cfg.llm_model,
        temperature=0.0,
        max_tokens=1000,
        response_format={"type": "json_object"},
        seed=cfg.seed,
    )

    payload = json.loads(result_response.message)
    keep_ids = set(payload.get("unique_ids", []))

    if state.return_type == 1:
        # 상품 고유 ID 목록만 반환
        summary_text = "상품 ID 목록만 반환하도록 요청되었습니다."
        logger.info("===== TRACE =====")
        logger.info(f"{trace}")

        return {"raw_result": {"product_meta": keep_ids, "user_info": []}}

    # return_type == 0인 경우 상품 메타데이터와 insight, summary, reasoning 리턴
    accepted_plans = [plan for plan in plans if plan.get("accepted")]
    num_accepted = len(accepted_plans)
    accepted_plans = json.dumps(accepted_plans, ensure_ascii=False)

    async def generate_insights() -> str:
        execution_summary = f"총 {len(plans)}단계 중 {num_accepted}개 성공"
        if state.private.retry.retry_count > 0:
            execution_summary += f", {state.private.retry.retry_count}회 재시도"
        prompt = INSIGHTS_PROMPT.format(
            user_query=original_question,
            search_results=accepted_plans,
            execution_summary=execution_summary,
        )
        response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": "사용자에게 도움이 되는 인사이트를 작성하세요.",
                },
            ],
            model=cfg.llm_model,
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "text"},
            seed=cfg.seed,
        )

        return response.message

    async def generate_summary() -> str:
        execution_stats = f"성공률: {num_accepted}/{len(plans)}"
        prompt = SUMMARY_PROMPT.format(
            user_query=original_question,
            search_results=accepted_plans,
            execution_stats=execution_stats,
        )
        response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "검색 결과를 요약하세요."},
            ],
            model=cfg.llm_model,
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "text"},
            seed=cfg.seed,
        )

        return response.message

    async def generate_reasoning() -> str:
        search_mode = (
            "기본 검색" if getattr(state, "expand_search", True) else "확장 검색"
        )
        recent_steps = "\n".join([f"• {item}" for item in trace[-8:]])
        retry_info = (
            f"재시도 {state.private.retry.retry_count}회"
            if state.private.retry.retry_count
            else "재시도 없음"
        )
        prompt = REASONING_PROMPT.format(
            user_query=original_question,
            search_case=search_mode,
            execution_steps=recent_steps,
            retry_info=retry_info,
        )
        response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "추론 과정을 설명해주세요."},
            ],
            model=cfg.llm_model,
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "text"},
            seed=cfg.seed,
        )

        return response.message

    insights, summary, reasoning = await asyncio.gather(
        generate_insights(),
        generate_summary(),
        generate_reasoning(),
    )

    trace.append("LLM 기반 후처리를 완료했습니다.")
    logger.info("===== TRACE =====")
    logger.info(f"{trace}")

    # TODO: 마지막 출력 단계에서 실패한 플랜도 함께 출력할지, 실패한 플랜은 제외하고 출력할지 검토 필요
    return {
        "insights": insights,
        "summary": summary,
        "reasoning": reasoning,
        "raw_result": {
            "product_meta": accepted_plans,
            "user_info": payload.get("user_info", []),
        },
        "updated_at": now.strftime("%Y-%m-%dT%H:%M"),
    }


def next_action_after_replan(state: OverallState) -> str:
    """replan 결과에 따라 다음 노드를 결정"""
    private_state = state.private

    next_action = getattr(private_state, "next_action_after_replan", None)
    if next_action in {"execute", "output"}:
        return next_action

    if private_state.plan:
        return "execute"

    return "output"
