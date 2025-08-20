from typing import Dict, Any
import json
from .state import OverallState, OutputState, InputState
from .configuration import Configuration as Config
from langchain_core.runnables import RunnableConfig
from .analayzer import replace_query_with_synonym
from .prompts import PLANNING_SYS_PROMPT
from .llm import async_create_chat_completion

"""
동작 플로우 sudo code

query -> init -> plan -> execute -> evaluate -> replan -> output

init: 초기 상태 설정 (동의어, 오타 치환)  
plan: 쿼리를 브레이크다운하여 subtasks 생성
execute: plan_node 에서 만들어진 subtasks 를 실행
evaluate: execute_node 에서 만들어진 결과를 평가
replan: evaluate_node 에서 평가 결과가 부정확할 경우 재계획
output: 최종 결과물 생성
"""

# Renamed to match the import in graph.py
async def init_node(state: InputState, config: RunnableConfig) -> OverallState:
    """초기 상태 설정, 동의어 처리해서 노드 초기화 진행"""
    config_obj = Config.from_runnable_config(config)
    query = state.query
    
    # 동의어 처리하는 부분
    updated_query = await replace_query_with_synonym(query[0] if isinstance(query, list) else query)
    
    return OverallState(
        query=[updated_query] if isinstance(updated_query, str) else updated_query,
        setting_date=state.setting_date,
        stream=state.stream
    )

async def plan_node(state: OverallState, config: RunnableConfig) -> OverallState:
    """쿼리를 브레이크다운하여 subtasks 생성"""
    config_obj = Config.from_runnable_config(config)
    query = state.query
    
    # Tool list should be provided from configuration or context
    tool_list_json = json.dumps([
        {"name": "search_tool", "description": "Search for information"},
        {"name": "analysis_tool", "description": "Analyze data"}
    ])
    
    prompt = PLANNING_SYS_PROMPT.substitute(tool_list_json=tool_list_json)
    
    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Query: {query}"}
    ]
    
    try:
        llm_response = await async_create_chat_completion(
            messages=messages,
            model=config_obj.llm_model,
            response_format={"type": "json_object"}
        )
        
        # Parse the response and update state
        plan_data = json.loads(llm_response.content)
        state.private.plan = plan_data.get("plan", [])
        
    except Exception as e:
        # Handle error gracefully
        state.private.plan = []
        state.private.loop_telemetry.last_error = str(e)
    
    return state

async def execute_node(state: OverallState, config: RunnableConfig) -> OverallState:
    """plan_node 에서 만들어진 subtasks 를 실행"""
    config_obj = Config.from_runnable_config(config)
    
    # Execute the planned tasks
    for task in state.private.plan:
        try:
            # Simulate task execution - replace with actual tool calls
            result = f"Executed: {task.get('tool', 'unknown')} - {task.get('reason', 'no reason')}"
            state.private.search_result.append({"task": task, "result": result})
        except Exception as e:
            state.private.loop_telemetry.last_error = str(e)
    
    return state

async def evaluate_node(state: OverallState, config: RunnableConfig) -> OverallState:
    """execute_node 에서 만들어진 결과를 평가"""
    config_obj = Config.from_runnable_config(config)
    
    # Evaluate results and determine if re-planning is needed
    if len(state.private.search_result) > 0:
        state.private.eval_status.accepted = True
        state.private.eval_status.score = 0.8
    else:
        state.private.eval_status.accepted = False
        state.private.eval_status.score = 0.0
    
    return state

async def replan_node(state: OverallState, config: RunnableConfig) -> OverallState:
    """evaluate_node 에서 평가 결과가 부정확할 경우 재계획"""
    config_obj = Config.from_runnable_config(config)
    
    # Increment retry count
    state.private.retry.retry_count += 1
    
    # If we haven't exceeded max retries, create new plan
    if state.private.retry.retry_count < state.private.retry.max_retries:
        # Reset plan for replanning
        state.private.plan = []
    
    return state

async def output_node(state: OverallState, config: RunnableConfig) -> OutputState:
    """최종 결과물 생성"""
    config_obj = Config.from_runnable_config(config)
    
    # Compile final output from search results
    raw_data = [result.get("result", "") for result in state.private.search_result]
    
    summary = f"Processed {len(state.private.search_result)} tasks"
    insights = "Generated insights from search results"
    reasoning = f"Used {len(state.private.plan)} steps to analyze the query"
    
    return OutputState(
        raw_data=raw_data,
        summary=summary,
        insights=insights,
        reasoning=reasoning
    )

# Add routing function for conditional edges
def replan_or_finish(state: OverallState) -> str:
    """Determine whether to replan or finish"""
    if (not state.private.eval_status.accepted and 
        state.private.retry.retry_count < state.private.retry.max_retries):
        return "replan"
    return "output"