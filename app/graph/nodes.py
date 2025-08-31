from typing import Dict, Any, List
from app.graph.states import OverallState, OutputState, InputState
from app.graph.configuration import Configuration as Config
from app.core.prompts import PLANNING_TEMPLATE, PLANNING_PROMPT, INSIGHTS_PROMPT, SUMMARY_PROMPT, REASONING_PROMPT
from app.graph.schema import Deps
import utils.json as json
from utils.timezone import KST
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from langchain.output_parsers import PydanticOutputParser
from app.graph.schema import Plan
import asyncio


# TODO: 동의어 키워드로 쪼개서 호출해서 처리하는 로직 필요
async def mock_up_replace_query_with_synonym(query: str) -> str:
    """동의어 처리"""
    return query


async def apreprocess_node(state: InputState, config: RunnableConfig) -> OverallState:
    """초기 상태 설정, 동의어 처리해서 노드 초기화 진행"""

    def convert_list_str(query: List[str]) -> str:
        return " ".join(query)

    query = convert_list_str(state.query)
    ## 동의어 처리하는 부분
    updated_query = await mock_up_replace_query_with_synonym(query=query)
    return {"query_synonym": updated_query}


async def retrieve_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    cfg = Config.from_runnable_config(config)
    query = state.query_synonym
    query_embedding = state.query_embedding[0]
    trace = state.private.trace or []
    
    from app.models.vectorstore.semantic_retrieval import SemanticSearchModel

    # expand_search에 따른 검색 전략 설정 (case1/case2)
    search_case = "case_1" if not state.expand_search else "case_2"
    trace.append(f"Few-shot retrieval with {search_case}")

    async with deps.postgres_db.get_async_session() as session:
        retrieved_examples: list[tuple[SemanticSearchModel, float]] = await deps.pgvector_models[
            0
        ].asearch_by_vector(session=session, embedding=query_embedding, similarity_cutoff=0.0)

    # case1/case2에 따른 예제 필터링
    filtered_examples = []
    for few_shot_example, score in retrieved_examples:
        cypher_query = few_shot_example.cypher_query
        
        # case1 (정확 매치): 단순한 MATCH 패턴만
        if not state.expand_search:
            # 복잡한 쿼리 패턴 제외 (집계, 다중 조인, 옵셔널 매치 등)
            if any(pattern in cypher_query.upper() for pattern in 
                   ["COUNT(", "SUM(", "AVG(", "GROUP BY", "OPTIONAL MATCH", "UNION", "WITH"]):
                continue  # case1에서는 제외
        
        filtered_examples.append({
            "query": few_shot_example.query,
            "cypher_query": cypher_query,
            "score": score,
        })
    
    trace.append(f"Retrieved {len(filtered_examples)} examples for {search_case} (from {len(retrieved_examples)} total)")
    
    # trace 업데이트
    private_dict = state.private.model_dump()
    private_dict["trace"] = trace
    
    return {
        "fewshot_examples": filtered_examples,
        "private": private_dict
    }


async def embedding_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    cfg = Config.from_runnable_config(config)

    embedding_client = deps.embed_client
    query_embedding_obj = await embedding_client.aembed(text=state.query_synonym)
    return {"query_embedding": query_embedding_obj.embeddings}


async def plan_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """쿼리를 브레이크다운하여 subtasks 생성"""
    cfg = Config.from_runnable_config(config)

    tools_description = deps.toolkit.get_tools_description()
    query = state.query_synonym
    parser = PydanticOutputParser(pydantic_object=Plan)
    prompt = PLANNING_PROMPT.partial(
        format_instructions=parser.get_format_instructions(),
        tool_list_json=json.dumps(tools_description),
    )
    system_message = prompt.format()
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
    plan = json.loads(llm_response.choices[0].message.content)
    plan = plan.get("plan", [])

    private_dict = state.private.model_dump()
    private_dict.update(
        {
            "plan": [*private_dict.get("plan", []), *plan],
        }
    )
    return {"private": private_dict}


async def to_output_node(state: OverallState, config: RunnableConfig) -> dict:
    """OverallState -> OutputState 스키마로 매핑"""
    plan = state.private.plan or []
    now = datetime.now(KST)

    return {
        "plan": plan,
        "raw_data": [],  # 아직 실행 전이니 빈 값
        "summary": "초기 계획만 생성되었습니다.",
        "insights": "",
        "reasoning": "LLM 계획 수립 단계만 수행됨.",
        "updated_at": now.strftime("%Y-%m-%dT%H:%M"),
        "version": "map-search-agent-dev",
    }


async def execute_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """plan_node 에서 만들어진 subtasks 를 실행"""
    cfg = Config.from_runnable_config(config)
    start_time = datetime.now()
    
    plan = state.private.plan or []
    search_results = []
    trace = state.private.trace or []
    
    if not plan:
        trace.append("No plan to execute")
        return {
            "private": {
                **state.private.model_dump(),
                "trace": trace,
                "search_result": search_results
            }
        }
    
    trace.append(f"Starting execution of {len(plan)} planned steps")
    
    # 계획의 각 step을 순차 실행 (map-search-agent의 execute_steps 로직 참고)
    for i, step in enumerate(plan):
        step_start_time = datetime.now()
        task_name = step.get("task", f"Step {i+1}")
        tool_name = step.get("tool")
        query_params = step.get("query", {})
        
        trace.append(f"Executing step {i+1}: {task_name}")
        
        try:
            if not tool_name:
                trace.append(f"Step {i+1}: No tool specified, skipping")
                continue
            
            # toolkit에서 사용 가능한 도구들 가져오기
            available_tools = deps.tools
            tool_instance = None
            
            # 도구 이름으로 매칭 (map-search-agent의 tool lookup 로직)
            for tool in available_tools:
                if hasattr(tool, 'name') and tool.name == tool_name:
                    tool_instance = tool
                    break
                elif hasattr(tool, '__class__') and tool.__class__.__name__ == tool_name:
                    tool_instance = tool
                    break
            
            if not tool_instance:
                error_msg = f"Tool '{tool_name}' not found in available tools"
                trace.append(f"Step {i+1}: {error_msg}")
                
                step_result = {
                    "step": i + 1,
                    "task": task_name,
                    "tool": tool_name,
                    "query": query_params,
                    "result": None,
                    "success": False,
                    "error": error_msg,
                    "execution_time_ms": 0
                }
                search_results.append(step_result)
                continue
            
            trace.append(f"Step {i+1}: Found tool '{tool_name}', executing with params: {query_params}")
            
            # 도구 실행 (map-search-agent의 tool invocation 패턴)
            result = None
            if hasattr(tool_instance, 'arun'):
                # 비동기 실행
                result = await tool_instance.arun(**query_params)
            elif hasattr(tool_instance, 'run'):
                # 동기 실행
                result = tool_instance.run(**query_params)
            elif hasattr(tool_instance, '__call__'):
                # callable 객체
                if asyncio.iscoroutinefunction(tool_instance):
                    result = await tool_instance(**query_params)
                else:
                    result = tool_instance(**query_params)
            else:
                raise ValueError(f"Tool {tool_name} has no executable method")
            
            execution_time_ms = int((datetime.now() - step_start_time).total_seconds() * 1000)
            
            # 성공 결과 저장
            step_result = {
                "step": i + 1,
                "task": task_name,
                "tool": tool_name,
                "query": query_params,
                "result": result,
                "success": True,
                "execution_time_ms": execution_time_ms
            }
            
            search_results.append(step_result)
            trace.append(f"Step {i+1}: Successfully executed in {execution_time_ms}ms")
            
        except Exception as e:
            execution_time_ms = int((datetime.now() - step_start_time).total_seconds() * 1000)
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            trace.append(f"Step {i+1}: {error_msg}")
            
            # 실패 결과 저장
            step_result = {
                "step": i + 1,
                "task": task_name,
                "tool": tool_name,
                "query": query_params,
                "result": None,
                "success": False,
                "error": str(e),
                "execution_time_ms": execution_time_ms
            }
            search_results.append(step_result)
    
    # 전체 실행 시간 계산
    total_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    trace.append(f"Execution completed: {len([r for r in search_results if r['success']])}/{len(search_results)} steps successful in {total_time_ms}ms")
    
    # private state 업데이트 (map-search-agent의 상태 관리 패턴)
    private_dict = state.private.model_dump()
    private_dict.update({
        "search_result": search_results,
        "trace": trace,
        "tool_latency_ms": total_time_ms
    })
    
    return {
        "private": private_dict
    }


async def evaluate_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """execute_node 에서 만들어진 결과를 평가 (map-search-agent의 평가 로직 참고)"""
    cfg = Config.from_runnable_config(config)
    
    search_results = state.private.search_result or []
    trace = state.private.trace or []
    
    trace.append("Starting evaluation of execution results")
    
    if not search_results:
        trace.append("No execution results to evaluate")
        eval_status = {
            "accepted": False,
            "score": 0.0,
            "detail": {"reason": "no_results", "message": "No execution results found"}
        }
    else:
        # map-search-agent의 결과 검증 로직 참고
        successful_steps = [r for r in search_results if r.get("success", False)]
        failed_steps = [r for r in search_results if not r.get("success", True)]
        
        total_steps = len(search_results)
        success_rate = len(successful_steps) / total_steps if total_steps > 0 else 0.0
        
        # 결과 데이터 품질 검사
        meaningful_results = []
        for result in successful_steps:
            result_data = result.get("result")
            if result_data is not None and result_data != "" and result_data != []:
                meaningful_results.append(result)
        
        has_meaningful_data = len(meaningful_results) > 0
        data_quality_score = len(meaningful_results) / len(successful_steps) if successful_steps else 0.0
        
        # map-search-agent 스타일 평가 기준
        score = 0.0
        detail = {
            "total_steps": total_steps,
            "successful_steps": len(successful_steps),
            "failed_steps": len(failed_steps),
            "meaningful_results": len(meaningful_results),
            "success_rate": success_rate,
            "data_quality": data_quality_score
        }
        
        # 점수 계산 (map-search-agent의 scoring 로직)
        if success_rate >= 1.0 and has_meaningful_data and data_quality_score >= 0.8:
            # 모든 스텝 성공 + 고품질 데이터
            score = 1.0
            accepted = True
            detail["reason"] = "excellent"
            detail["message"] = f"All {total_steps} steps successful with high-quality data"
        elif success_rate >= 0.8 and has_meaningful_data and data_quality_score >= 0.6:
            # 대부분 성공 + 양질 데이터
            score = 0.8
            accepted = True
            detail["reason"] = "good"
            detail["message"] = f"High success rate with good data quality"
        elif success_rate >= 0.5 and has_meaningful_data:
            # 절반 이상 성공 + 데이터 있음
            score = 0.6
            accepted = True
            detail["reason"] = "acceptable"
            detail["message"] = f"Partial success with some meaningful data"
        elif has_meaningful_data:
            # 데이터는 있지만 성공률 낮음 - 재시도 고려
            score = 0.3
            accepted = False
            detail["reason"] = "low_success_rate"
            detail["message"] = f"Low success rate: {success_rate:.1%}, but has some data"
        else:
            # 의미있는 데이터 없음 - 재계획 필요
            score = 0.1
            accepted = False
            detail["reason"] = "no_meaningful_data"
            detail["message"] = "No meaningful data returned from any step"
        
        eval_status = {
            "accepted": accepted,
            "score": score,
            "detail": detail
        }
        
        trace.append(f"Evaluation: score={score:.2f}, accepted={accepted}, reason={detail['reason']}")
    
    # retry budget 관리 (map-search-agent의 retry 패턴)
    retry_budget = state.private.retry.model_dump()
    if not eval_status["accepted"]:
        retry_budget["retry_count"] = retry_budget.get("retry_count", 0) + 1
        trace.append(f"Incrementing retry count: {retry_budget['retry_count']}/{retry_budget.get('max_retries', 3)}")
    
    # private state 업데이트
    private_dict = state.private.model_dump()
    private_dict.update({
        "eval_status": eval_status,
        "retry": retry_budget,
        "trace": trace
    })
    
    return {
        "private": private_dict
    }


async def replan_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """evaluate_node 에서 평가 결과가 부정확할 경우 재계획 (map-search-agent의 replan 로직 참고)"""
    cfg = Config.from_runnable_config(config)
    
    trace = state.private.trace or []
    search_results = state.private.search_result or []
    eval_status = state.private.eval_status
    
    # 실패 원인 분석 (map-search-agent의 failure analysis)
    failure_reason = eval_status.detail.get("reason", "unknown")
    failed_steps = [r for r in search_results if not r.get("success", True)]
    
    trace.append(f"Starting replanning due to: {failure_reason}")
    
    # 실패 모드 히스토리 업데이트 (telemetry)
    loop_telemetry = state.private.loop_telemetry.model_dump()
    failure_hist = loop_telemetry.get("failure_mode_hist", {})
    failure_hist[failure_reason] = failure_hist.get(failure_reason, 0) + 1
    loop_telemetry["failure_mode_hist"] = failure_hist
    loop_telemetry["last_error"] = eval_status.detail.get("message", "")
    
    # 새로운 계획 생성을 위한 컨텍스트 구성 (map-search-agent 방식)
    tools_description = deps.toolkit.get_tools_description()
    query = state.query_synonym
    
    # 실패 정보를 포함한 재계획 프롬프트
    execution_feedback = f"""
원본 쿼리: {query}

이전 실행 결과 분석:
- 총 단계: {len(search_results)}
- 성공한 단계: {len([r for r in search_results if r.get('success', False)])}
- 실패한 단계: {len(failed_steps)}
- 실패 원인: {failure_reason}
- 성공률: {len([r for r in search_results if r.get('success', False)]) / len(search_results) * 100:.1f}%

실패한 단계들의 상세 정보:"""
    
    if failed_steps:
        for step in failed_steps:
            execution_feedback += f"""
- 단계 {step.get('step')}: {step.get('task', 'Unknown task')}
  도구: {step.get('tool', 'Unknown tool')}
  오류: {step.get('error', 'No error details')}"""
    
    execution_feedback += f"""

성공한 단계들:"""
    successful_steps = [r for r in search_results if r.get("success", False)]
    if successful_steps:
        for step in successful_steps[:3]:  # 최대 3개만 표시
            execution_feedback += f"""
- 단계 {step.get('step')}: {step.get('task', 'Unknown task')} (성공)"""
    
    execution_feedback += f"""

위 분석을 바탕으로 실패를 해결하고 더 나은 결과를 얻을 수 있는 개선된 계획을 수립하세요.
가능하다면 실패한 도구 대신 다른 도구를 사용하거나, 파라미터를 조정하세요.
"""
    
    try:
        # 재계획 생성 (map-search-agent의 replanning logic)
        parser = PydanticOutputParser(pydantic_object=Plan)
        prompt = PLANNING_PROMPT.partial(
            format_instructions=parser.get_format_instructions(),
            tool_list_json=json.dumps(tools_description),
        )
        system_message = prompt.format()
        
        llm_response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": execution_feedback},
            ],
            model=cfg.llm_model,
            temperature=0.2,  # 약간의 창의성으로 다른 접근법 시도
            max_tokens=2000,
            response_format={"type": "json_object"},
            seed=cfg.seed,
        )
        
        new_plan = json.loads(llm_response.choices[0].message.content)
        new_plan = new_plan.get("plan", [])
        
        trace.append(f"Generated new plan with {len(new_plan)} steps")
        
        # best_so_far 업데이트 (현재 결과가 이전보다 나으면 보존)
        current_score = eval_status.get("score", 0.0)
        best_so_far = state.private.best_so_far.model_dump()
        
        if current_score > best_so_far.get("score", -1.0):
            best_so_far.update({
                "score": current_score,
                "output": {"search_results": search_results},
                "reason": f"Better score: {current_score:.2f}",
                "plan_snapshot": state.private.plan
            })
            trace.append(f"Updated best result with score: {current_score:.2f}")
        
        # 새 계획으로 상태 재설정 (map-search-agent의 state reset)
        private_dict = state.private.model_dump()
        private_dict.update({
            "plan": new_plan,  # 새로운 계획으로 교체
            "search_result": [],  # 실행 결과 초기화
            "trace": trace,
            "loop_telemetry": loop_telemetry,
            "best_so_far": best_so_far,
            "eval_status": {  # 평가 상태 초기화
                "accepted": False,
                "score": -1.0,
                "detail": {}
            }
        })
        
        trace.append("Replanning completed, ready for re-execution")
        
    except Exception as e:
        error_msg = f"Replanning failed: {str(e)}"
        trace.append(error_msg)
        loop_telemetry["last_error"] = error_msg
        
        # 재계획 실패시 기존 상태 유지하고 종료 유도
        private_dict = state.private.model_dump()
        private_dict.update({
            "trace": trace,
            "loop_telemetry": loop_telemetry,
            "eval_status": {
                "accepted": True,  # 강제 종료
                "score": 0.0,
                "detail": {"reason": "replan_failed", "message": error_msg}
            }
        })
    
    return {
        "private": private_dict
    }


async def output_node(state: OverallState, deps: Deps, config: RunnableConfig) -> dict:
    """최종 결과물 생성 - return_type에 따른 분기 처리"""
    cfg = Config.from_runnable_config(config)
    now = datetime.now(KST)
    
    search_results = state.private.search_result or []
    trace = state.private.trace or []
    
    trace.append(f"Generating final output for return_type={state.return_type}")
    
    # 성공한 결과들에서 데이터 추출
    successful_results = [r for r in search_results if r.get("success", False)]
    
    # 공통 데이터 추출
    product_meta = []
    user_info_data = []
    
    # 검색 결과에서 상품 정보 추출
    for result in successful_results:
        result_data = result.get("result", {})
        if isinstance(result_data, dict):
            if "products" in result_data:
                product_meta.extend(result_data["products"])
            elif "product_meta" in result_data:
                product_meta.extend(result_data["product_meta"])
        elif isinstance(result_data, list):
            product_meta.extend(result_data)
    
    # user_info 처리
    if state.user_info:
        user_info_results = [r for r in successful_results if "user" in r.get("tool", "").lower()]
        for result in user_info_results:
            user_data = result.get("result", {})
            if user_data:
                user_info_data.append(user_data)
    
    # raw_result 구성
    raw_result = {
        "search_results": successful_results,
        "execution_summary": {
            "total_steps": len(search_results),
            "successful_steps": len(successful_results),
            "search_case": "case_1" if not state.expand_search else "case_2"
        }
    }
    
    # return_type=1: product_id만 반환 (LLM 호출 생략)
    if state.return_type == 1:
        # product_meta에서 ID만 추출
        product_ids = []
        for product in product_meta:
            if isinstance(product, dict) and "id" in product:
                product_ids.append(product["id"])
            elif isinstance(product, str):
                product_ids.append(product)
        
        return {
            "raw_data": raw_result,
            "product_meta": product_ids,  # List[str] 형태
            "user_info_data": user_info_data,
        }
    
    # return_type=0: 전체 응답 (LLM 기반 콘텐츠 생성)
    else:
        search_results = state.private.search_result or []
        best_so_far = state.private.best_so_far
        
        # raw_data 구성 로직
        raw_data = {}
        if successful_results:
            raw_data = {
                "search_results": successful_results,
                "execution_summary": {
                    "total_steps": len(search_results),
                    "successful_steps": len(successful_results),
                    "failed_steps": len(search_results) - len(successful_results),
                    "total_execution_time_ms": state.private.tool_latency_ms,
                    "retry_count": state.private.retry.retry_count,
                    "search_case": "case_1" if not state.expand_search else "case_2"
                },
                "telemetry": {
                    "failure_history": state.private.loop_telemetry.failure_mode_hist,
                    "last_error": state.private.loop_telemetry.last_error
                }
            }
            
            if best_so_far.score > 0.5:
                raw_data["best_result"] = best_so_far.output or {}
                raw_data["best_score"] = best_so_far.score
        else:
            raw_data = {
                "search_results": [],
                "execution_summary": {
                    "total_steps": len(search_results),
                    "successful_steps": 0,
                    "failed_steps": len(search_results),
                    "total_execution_time_ms": state.private.tool_latency_ms or 0,
                    "retry_count": state.private.retry.retry_count,
                    "search_case": "case_1" if not state.expand_search else "case_2"
                },
                "error_analysis": {
                    "failure_history": state.private.loop_telemetry.failure_mode_hist,
                    "last_error": state.private.loop_telemetry.last_error
                }
            }
        
        # LLM 기반 콘텐츠 생성 (return_type=0만)
        trace.append("Generating LLM-based insights, summary, and reasoning")
        
        # 공통 데이터 준비
        user_query = " ".join(state.query) if isinstance(state.query, list) else str(state.query)
        search_results_summary = json.dumps(successful_results, ensure_ascii=False, indent=2)
        
        # Insights 생성
        execution_summary = f"총 {len(search_results)}단계 중 {len(successful_results)}개 성공"
        if state.private.retry.retry_count > 0:
            execution_summary += f", {state.private.retry.retry_count}회 재시도"
        
        insights_prompt = INSIGHTS_PROMPT.format(
            user_query=user_query,
            search_results=search_results_summary,
            execution_summary=execution_summary
        )
        
        insights_response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": insights_prompt},
                {"role": "user", "content": "사용자의 검색 의도를 분석하고 가성비 관점에서 적절한 답변을 제공해주세요."}
            ],
            model=cfg.llm_model,
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "text"},
            seed=cfg.seed,
        )
        insights = insights_response.choices[0].message.content
        
        # Summary 생성  
        execution_stats = f"성공률: {len(successful_results)}/{len(search_results)}"
        if search_results:
            avg_time = sum(r.get("execution_time_ms", 0) for r in search_results) / len(search_results)
            execution_stats += f", 평균 응답시간: {avg_time:.0f}ms"
        
        summary_prompt = SUMMARY_PROMPT.format(
            user_query=user_query,
            search_results=search_results_summary,
            execution_stats=execution_stats
        )
        
        summary_response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": summary_prompt},
                {"role": "user", "content": "검색 결과의 주요 특징과 제한사항을 요약해주세요."}
            ],
            model=cfg.llm_model,
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "text"},
            seed=cfg.seed,
        )
        summary = summary_response.choices[0].message.content
        
        # Reasoning 생성
        search_case = "Case 1 (정확 매치)" if not state.expand_search else "Case 2 (조건 완화)"
        execution_steps = "\n".join([f"• {t}" for t in trace[-8:]])  # 최근 8개 단계
        retry_info = f"{state.private.retry.retry_count}회 재시도" if state.private.retry.retry_count > 0 else "재시도 없음"
        
        reasoning_prompt = REASONING_PROMPT.format(
            user_query=user_query,
            search_case=search_case,
            execution_steps=execution_steps,
            retry_info=retry_info
        )
        
        reasoning_response = await deps.llm_client.agenerate_response(
            messages=[
                {"role": "system", "content": reasoning_prompt},
                {"role": "user", "content": "검색 과정의 추론 근거와 실행 과정을 설명해주세요."}
            ],
            model=cfg.llm_model,
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "text"},
            seed=cfg.seed,
        )
        reasoning = reasoning_response.choices[0].message.content
        
        trace.append("Completed LLM-based content generation")
        
        # return_type=0: LLM 생성 콘텐츠로 응답
        return {
            "insights": insights,
            "summary": summary,
            "reasoning": reasoning,
            "raw_data": raw_data,
            "product_meta": product_meta,  # List[Dict] 형태
            "user_info_data": user_info_data,
            "updated_at": now.strftime("%Y-%m-%dT%H:%M"),
        }


def should_replan(state: OverallState) -> str:
    """평가 결과를 바탕으로 재계획 여부 결정 (map-search-agent의 조건부 라우팅)"""
    eval_status = state.private.eval_status
    retry_budget = state.private.retry
    
    # 결과가 수용 가능한 경우 종료
    if eval_status.accepted:
        return "output"
    
    # 재시도 예산이 남아있는 경우 재계획
    if retry_budget.retry_count < retry_budget.max_retries:
        return "replan"
    
    # 재시도 한계 도달시 현재 결과로 종료
    return "output"
