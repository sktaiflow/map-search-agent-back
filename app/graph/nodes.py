from typing import Dict, Any, List
import asyncio
import json
from datetime import datetime

from app.graph.states import OverallState, InputState
from app.graph.configuration import Configuration as Config
from app.core.prompts import (
    PLANNING_PROMPT,
    INSIGHTS_PROMPT,
    SUMMARY_PROMPT,
    REASONING_PROMPT,
)
from app.graph.schema import Deps
from utils.timezone import KST
from langchain_core.runnables import RunnableConfig
from langchain.output_parsers import PydanticOutputParser
from app.graph.schema import Plan


def _format_tool_overview(tools: List[Dict[str, Any]]) -> str:
    if not tools:
        return "현재 사용 가능한 도구가 없습니다."

    lines: List[str] = []
    for tool in tools:
        name = tool.get("name", "")
        description = tool.get("description", "")
        lines.append(f"- {name}: {description}")

        args_schema = tool.get("args_schema") or {}
        properties = args_schema.get("properties") or {}
        required = set(args_schema.get("required") or [])

        for arg_name, metadata in properties.items():
            if not isinstance(metadata, dict):
                metadata = {}
            arg_type = metadata.get("type")
            if not arg_type and isinstance(metadata.get("anyOf"), list):
                arg_type = ", ".join(
                    entry.get("type")
                    for entry in metadata["anyOf"]
                    if isinstance(entry, dict) and entry.get("type")
                )
            arg_desc = metadata.get("description") or ""
            req_suffix = " (required)" if arg_name in required else ""
            type_suffix = f" [{arg_type}]" if arg_type else ""
            lines.append(f"    • {arg_name}{req_suffix}{type_suffix}: {arg_desc}")

    return "\n".join(lines)


def _build_tool_usage_examples(tools: List[Dict[str, Any]]) -> str:
    example_steps: List[Dict[str, Any]] = []

    for index, tool in enumerate(tools, start=1):
        step = {
            "step": index,
            "tool": tool.get("name", ""),
            "reason": (tool.get("description") or "예시 작업 설명"),
            "mode": "sequential" if index == 1 else "parallel",
        }

        args_schema = tool.get("args_schema") or {}
        properties = args_schema.get("properties") or {}
        if properties:
            args_example: Dict[str, Any] = {}
            for arg_name, metadata in properties.items():
                placeholder = "<value>"
                if isinstance(metadata, dict):
                    arg_type = metadata.get("type")
                    if arg_type in {"integer", "number"}:
                        placeholder = 0
                    elif arg_type == "boolean":
                        placeholder = True
                    elif arg_type == "array":
                        placeholder = ["<item>"]
                    elif arg_type == "object":
                        placeholder = {"key": "value"}
                    else:
                        placeholder = f"<{arg_type or 'value'}>"
                args_example[arg_name] = placeholder
            step["args"] = args_example

        example_steps.append(step)

    if not example_steps:
        example_steps.append(
            {
                "step": 1,
                "tool": "available_tool_name",
                "reason": "도구 사용 예시",
                "mode": "sequential",
            }
        )

    return json.dumps({"plan": example_steps}, ensure_ascii=False, indent=2)


def _make_serializable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _make_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_make_serializable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


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

    # TODO: 툴 설명을 매번 생성하지 말고 캐싱해서 사용할 수 있지 않으려나?
    tools_description = deps.toolkit.get_tools_description()
    tool_overview = _format_tool_overview(tools_description)
    tool_schema_json = json.dumps(tools_description, ensure_ascii=False, indent=2)
    tool_examples = _build_tool_usage_examples(tools_description)
    # query = state.query_synonym
    trace = list(state.private.trace or [])

    # LLM에게 전달할 출력 포맷 지정 (Pydantic Parser 이용)
    parser = PydanticOutputParser(pydantic_object=Plan)
    prompt = PLANNING_PROMPT.partial(
        user_id=state.user_id,
        format_instructions=parser.get_format_instructions(),
        tool_overview=tool_overview,
        tool_schema_json=tool_schema_json,
        tool_usage_examples=tool_examples,
    )
    system_message = prompt.format()

    trace.append("계획 수립을 위한 LLM 호출을 시작합니다.")
    # TODO: 툴을 여기에서 실어서 보내는 것도 고려 (지금은 PLANNING_TEMPLATE에 아예 넣어져있음)
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
    )

    print("############# system_message:", system_message, "\n\n")

    try:
        parsed_plan = json.loads(llm_response.message)
    except json.JSONDecodeError:
        # JSON 디코딩 실패 시 안전하게 빈 계획으로 초기화
        trace.append("LLM 응답을 JSON으로 파싱하지 못해 빈 계획을 사용합니다.")
        plan_steps: List[Dict[str, Any]] = []
    else:
        # 정상 파싱된 경우에도 리스트 구조인지 한 번 더 검증
        raw_plan = parsed_plan.get("plan", []) if isinstance(parsed_plan, dict) else []
        plan_steps = raw_plan if isinstance(raw_plan, list) else []
        trace.append(f"총 {len(plan_steps)}개의 단계가 생성되었습니다.")

    private_dict = state.private.model_dump()
    private_dict.update(
        {
            "plan": plan_steps,
            "trace": trace,
        }
    )

    return {"private": private_dict}


# TODO: 사용하지 않는 코드라면 제거하기
async def to_output_node(state: OverallState, config: RunnableConfig) -> dict:
    """OverallState -> OutputState 스키마로 매핑"""
    plan = state.private.plan or []
    now = datetime.now(KST)

    return {
        "plan": plan,
        "raw_data": {},
        "summary": "초기 계획만 생성되었습니다.",
        "insights": "",
        "reasoning": "LLM 계획 수립 단계만 수행됨.",
        "updated_at": now.strftime("%Y-%m-%dT%H:%M"),
        "version": "map-search-agent-dev",
    }


async def execute_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    plan = list(state.private.plan or [])
    trace = list(state.private.trace or [])
    search_results: List[Dict[str, Any]] = list(state.private.search_result or [])
    total_elapsed = state.private.tool_latency_ms or 0

    if not plan:
        trace.append("실행할 계획이 없어 스킵합니다.")
        private_state = state.private.model_dump()
        private_state.update({"trace": trace, "search_result": search_results})
        return {"private": private_state}

    current_step = plan[0]
    remaining_plan = plan[1:]

    step_index = current_step.get("step") or (len(search_results) + 1)
    task_name = current_step.get("task", f"단계 {step_index}")
    tool_name = current_step.get("tool")
    query_params = current_step.get("args", current_step.get("query", {})) or {}

    trace.append(f"{step_index}단계 실행 시작: {task_name}")
    step_start = datetime.now()

    def _record_result(
        *,
        success: bool,
        result: Any = None,
        error: str | None = None,
        latency_ms: int = 0,
    ) -> None:
        search_results.append(
            {
                "step": step_index,
                "task": task_name,
                "tool": tool_name,
                "query": query_params,
                "result": result,
                "success": success,
                "error": error,
                "execution_time_ms": latency_ms,
            }
        )

    if not tool_name:
        trace.append(f"{step_index}단계에 도구가 없어 건너뜁니다.")
        _record_result(success=False, error="도구 미지정")
    else:
        tool_instance = next(
            (
                tool
                for tool in deps.tools
                if getattr(tool, "name", None) == tool_name
                or tool.__class__.__name__ == tool_name
            ),
            None,
        )

        if not tool_instance:
            trace.append(f"{step_index}단계 실패: {tool_name} 도구를 찾지 못했습니다.")
            _record_result(success=False, error="도구 미존재")
        else:
            trace.append(f"{step_index}단계에서 {tool_name} 실행: {query_params}")
            try:
                result = await tool_instance.arun(query_params)

                latency = int((datetime.now() - step_start).total_seconds() * 1000)
                trace.append(f"{step_index}단계 성공 ({latency}ms)")
                _record_result(success=True, result=result, latency_ms=latency)
                total_elapsed += latency
            except Exception as error:
                latency = int((datetime.now() - step_start).total_seconds() * 1000)
                message = f"{tool_name} 실행 중 오류 발생: {error}"
                trace.append(f"{step_index}단계 실패: {message}")
                _record_result(success=False, error=str(error), latency_ms=latency)
                total_elapsed += latency

    private_state = state.private.model_dump()
    private_state.update(
        {
            "plan": remaining_plan,
            "search_result": search_results,
            "trace": trace,
            "tool_latency_ms": total_elapsed,
        }
    )

    return {"private": private_state}


async def evaluate_node(
    state: OverallState, deps: Deps, config: RunnableConfig
) -> dict:
    """execute_node 결과를 기반으로 간단 평가"""
    trace = list(state.private.trace or [])
    search_results = list(state.private.search_result or [])
    trace.append("실행 결과 평가를 시작합니다.")

    if not search_results:
        eval_status = {
            "accepted": False,
            "score": 0.0,
            "detail": {
                "reason": "no_results",
                "message": "평가할 실행 결과가 없습니다.",
            },
        }
        trace.append("평가 대상이 없어 재계획이 필요합니다.")
    else:
        successful = [result for result in search_results if result.get("success")]
        has_meaningful = any(
            result.get("result")
            for result in successful
            if result.get("result") not in ("I don't know the answer.", [], None)
        )

        if has_meaningful:
            eval_status = {
                "accepted": True,
                "score": 1.0,
                "detail": {
                    "reason": "success",
                    "message": f"의미 있는 결과 {len(successful)}건 확보",
                    "total_steps": len(search_results),
                    "successful_steps": len(successful),
                },
            }
            trace.append("의미 있는 결과가 확인되었습니다.")
        else:
            eval_status = {
                "accepted": False,
                "score": 0.0,
                "detail": {
                    "reason": "no_data",
                    "message": "의미 있는 데이터를 찾지 못했습니다.",
                    "total_steps": len(search_results),
                    "successful_steps": len(successful),
                },
            }
            trace.append("결과가 부족하여 재계획이 필요합니다.")

    retry_budget = state.private.retry.model_dump()
    if not eval_status["accepted"]:
        retry_budget["retry_count"] = retry_budget.get("retry_count", 0) + 1
        trace.append(
            f"재시도 횟수 {retry_budget['retry_count']}/{retry_budget.get('max_retries', 3)}"
        )

    private_state = state.private.model_dump()
    private_state.update(
        {"eval_status": eval_status, "retry": retry_budget, "trace": trace}
    )

    # print("########### [evaluate] private_state:", private_state, "\n\n")

    return {"private": private_state}


async def replan_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """evaluate_node 결과가 미흡할 때 재계획 수행"""
    cfg = Config.from_runnable_config(config)
    trace = list(state.private.trace or [])
    search_results = list(state.private.search_result or [])
    eval_status = state.private.eval_status

    failure_detail = getattr(eval_status, "detail", {}) or {}
    failure_reason = failure_detail.get("reason", "unknown")
    failed_steps = [
        result for result in search_results if not result.get("success", True)
    ]

    trace.append(f"재계획을 시작합니다. 사유: {failure_reason}")

    loop_telemetry = state.private.loop_telemetry.model_dump()
    failure_hist = dict(loop_telemetry.get("failure_mode_hist", {}))
    failure_hist[failure_reason] = failure_hist.get(failure_reason, 0) + 1
    loop_telemetry["failure_mode_hist"] = failure_hist
    loop_telemetry["last_error"] = failure_detail.get("message", "")

    tools_description = deps.toolkit.get_tools_description()
    tool_overview = _format_tool_overview(tools_description)
    tool_schema_json = json.dumps(tools_description, ensure_ascii=False, indent=2)
    tool_examples = _build_tool_usage_examples(tools_description)
    if state.query_synonym:
        query = state.query_synonym
    elif isinstance(state.query, list):
        query = " ".join(state.query)
    else:
        query = state.query
    total_steps = len(search_results)
    success_steps = len([result for result in search_results if result.get("success")])
    success_rate = 0.0 if total_steps == 0 else (success_steps / total_steps) * 100

    feedback_lines = [
        f"원본 쿼리: {query}",
        "",
        "이전 실행 결과:",
        f"- 총 단계: {total_steps}",
        f"- 성공한 단계: {success_steps}",
        f"- 실패한 단계: {len(failed_steps)}",
        f"- 실패 원인: {failure_reason}",
        f"- 성공률: {success_rate:.1f}%",
        "",
        "실패 단계 세부사항:",
    ]

    if failed_steps:
        for step in failed_steps:
            feedback_lines.append(
                f"- 단계 {step.get('step')}: {step.get('task', '알 수 없음')} / 오류: {step.get('error', '세부 정보 없음')}"
            )
    else:
        feedback_lines.append("- 명시적인 실패 단계는 없었습니다.")

    feedback_lines.append("")
    feedback_lines.append("성공 단계 요약:")
    successful_steps = [
        result for result in search_results if result.get("success", False)
    ]
    if successful_steps:
        for step in successful_steps[:3]:
            feedback_lines.append(
                f"- 단계 {step.get('step')}: {step.get('task', '알 수 없음')} (성공)"
            )
    else:
        feedback_lines.append("- 성공한 단계가 없습니다.")

    feedback_lines.append("")
    feedback_lines.append("위 정보를 참고하여 실패를 보완할 새로운 계획을 제안하세요.")

    if search_results:
        latest_step = search_results[-1]
        step_snapshot = {
            "step": latest_step.get("step"),
            "tool": latest_step.get("tool"),
            "input": _make_serializable(latest_step.get("query")),
            "result": _make_serializable(latest_step.get("result")),
            "success": latest_step.get("success"),
            "error": latest_step.get("error"),
        }
        feedback_lines.append("")
        feedback_lines.append("마지막 실행 상세 (입력 및 결과):")
        feedback_lines.append(
            json.dumps(step_snapshot, ensure_ascii=False, indent=2)
        )

    execution_feedback = "\n".join(feedback_lines)

    try:
        parser = PydanticOutputParser(pydantic_object=Plan)
        prompt = PLANNING_PROMPT.partial(
            user_id=state.user_id,
            format_instructions=parser.get_format_instructions(),
            tool_overview=tool_overview,
            tool_schema_json=tool_schema_json,
            tool_usage_examples=tool_examples,
        )
        system_message = prompt.format()
        llm_response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": execution_feedback},
            ],
            model=cfg.llm_model,
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
            seed=cfg.seed,
        )

        new_plan = json.loads(llm_response.message).get("plan", [])
        trace.append(f"재계획 완료: {len(new_plan)}개 단계 생성")

        private_state = state.private.model_dump()
        private_state.update(
            {
                "plan": new_plan,
                "search_result": [],
                "trace": trace,
                "loop_telemetry": loop_telemetry,
                "eval_status": {"accepted": False, "score": -1.0, "detail": {}},
            }
        )
        return {"private": private_state}

    except Exception as error:
        message = f"재계획 중 오류 발생: {error}"
        trace.append(message)
        loop_telemetry["last_error"] = message

        private_state = state.private.model_dump()
        private_state.update(
            {
                "trace": trace,
                "loop_telemetry": loop_telemetry,
                "eval_status": {
                    "accepted": True,
                    "score": 0.0,
                    "detail": {"reason": "replan_failed", "message": message},
                },
            }
        )
        return {"private": private_state}


async def output_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """최종 결과물을 생성"""
    cfg = Config.from_runnable_config(config)
    now = datetime.now(KST)

    plan = list(state.private.plan or [])
    search_results = list(state.private.search_result or [])
    trace = list(state.private.trace or [])
    trace.append("최종 응답 생성을 시작합니다.")

    successful_results = [result for result in search_results if result.get("success")]
    product_meta: List[Dict[str, Any]] = []
    user_info_data: List[Dict[str, Any]] = []

    for result in successful_results:
        payload = result.get("result")
        if isinstance(payload, dict):
            if "products" in payload:
                product_meta.extend(payload.get("products", []))
            elif "product_meta" in payload:
                product_meta.extend(payload.get("product_meta", []))
        elif isinstance(payload, list):
            product_meta.extend(payload)

    if getattr(state, "user_info_yn", True):
        for result in successful_results:
            tool_name = (result.get("tool") or "").lower()
            if "user" in tool_name:
                data = result.get("result")
                if data:
                    user_info_data.append(data)

    raw_result = {
        "search_results": successful_results,
        "execution_summary": {
            "total_steps": len(search_results),
            "successful_steps": len(successful_results),
            "failed_steps": len(search_results) - len(successful_results),
            "total_execution_time_ms": state.private.tool_latency_ms,
        },
        "debug_trace": trace,
    }

    return_type = getattr(state, "return_type", 2)

    if return_type == 1:
        product_ids: List[str] = []
        for item in product_meta:
            if isinstance(item, dict) and "id" in item:
                product_ids.append(str(item["id"]))
            elif isinstance(item, str):
                product_ids.append(item)

        summary_text = "상품 ID 목록만 반환하도록 요청되었습니다."
        return {
            "plan": plan,
            "raw_data": raw_result,
            "summary": summary_text,
            "insights": summary_text,
            "reasoning": "추가 요약 없이 원시 결과를 전달합니다.",
            "updated_at": now.strftime("%Y-%m-%dT%H:%M"),
            "version": "map-search-agent-dev",
            "fewshot_examples": state.fewshot_examples,
            "product_meta": product_ids,
            "return_type": return_type,
            "user_info_data": user_info_data,
        }

    raw_data = {
        "search_results": successful_results,
        "execution_summary": {
            "total_steps": len(search_results),
            "successful_steps": len(successful_results),
            "failed_steps": len(search_results) - len(successful_results),
            "total_execution_time_ms": state.private.tool_latency_ms,
            "retry_count": state.private.retry.retry_count,
        },
        "debug_trace": trace,
    }

    user_query = state.query if isinstance(state.query, str) else " ".join(state.query)
    results_text = json.dumps(successful_results, ensure_ascii=False)

    async def generate_insights() -> str:
        execution_summary = (
            f"총 {len(search_results)}단계 중 {len(successful_results)}개 성공"
        )
        if state.private.retry.retry_count > 0:
            execution_summary += f", {state.private.retry.retry_count}회 재시도"
        prompt = INSIGHTS_PROMPT.format(
            user_query=user_query,
            search_results=results_text,
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
        execution_stats = f"성공률: {len(successful_results)}/{len(search_results)}"
        prompt = SUMMARY_PROMPT.format(
            user_query=user_query,
            search_results=results_text,
            execution_stats=execution_stats,
        )
        response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "검색 결과를 요약하세요."},
            ],
            model=cfg.llm_model,
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "text"},
            seed=cfg.seed,
        )

        return response.message

    async def generate_reasoning() -> str:
        search_mode = (
            "기본 검색" if getattr(state, "search_type", True) else "확장 검색"
        )
        recent_steps = "\n".join([f"• {item}" for item in trace[-8:]])
        retry_info = (
            f"재시도 {state.private.retry.retry_count}회"
            if state.private.retry.retry_count
            else "재시도 없음"
        )
        prompt = REASONING_PROMPT.format(
            user_query=user_query,
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

    return {
        "plan": plan,
        "raw_data": raw_data,
        "summary": summary,
        "insights": insights,
        "reasoning": reasoning,
        "updated_at": now.strftime("%Y-%m-%dT%H:%M"),
        "version": "map-search-agent-dev",
        "fewshot_examples": state.fewshot_examples,
        "product_meta": product_meta,
        "return_type": return_type,
        "user_info_data": user_info_data,
    }


def should_replan(state: OverallState) -> str:
    """평가 결과에 따라 재계획할지 결정"""
    eval_status = state.private.eval_status
    if isinstance(eval_status, dict):
        accepted = eval_status.get("accepted", False)
    else:
        accepted = eval_status.accepted

    if accepted:
        return "output"

    retry_budget = state.private.retry
    if isinstance(retry_budget, dict):
        retry_count = retry_budget.get("retry_count", 0)
        max_retries = retry_budget.get("max_retries", 3)
    else:
        retry_count = retry_budget.retry_count
        max_retries = retry_budget.max_retries

    if retry_count < max_retries:
        return "replan"
    return "output"
