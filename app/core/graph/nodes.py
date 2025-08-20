from typing import Dict, Any
from .state import OverallState, OutputState, InputState
from .configuration import Configuration as Config
from langchain_core.runnables import RunnableConfig
from app.core.prompts import PLANNING_SYS_PROMPT

"""
동작 플로우 sudo code
query -> init -> plan -> execute -> evaluate -> replan -> output
preprocess_node: 초기 상태 설정 (동의어, 오타 치환)
"""


#TODO: 이름을 preprocess_node 로 변경 (추후)
def preprocess_node(state: InputState, config: RunnableConfig) -> OverallState:
    """초기 상태 설정, 동의어 처리해서 노드 초기화 진행"""
    config = Config.from_runnable_config(config)
    query = state.query
    ## 동의어 처리하는 부분
    updated_query = replace_query_with_synonym(query)

    return {"query": updated_query}


#TODO: 동의어 처리 필요
async def preprocess_node(state: InputState, config: RunnableConfig) -> OverallState:
    """초기 상태 설정, 동의어 처리해서 노드 초기화 진행"""
    config = Config.from_runnable_config(config)
    query = state.query

    ## 동의어 처리하는 부분
    updated_query = await replace_query_with_synonym(query)

    return {"query": updated_query}

## 
def plan_node(state: OverallState) -> OverallState:
    """쿼리를 브레이크다운하여 subtasks 생성"""

    query = state.query

    prompt = PLANNING_SYS_PROMPT.substitute(tool_list_json=)

    llm_response = await llm.ainvoke(prompt)

    return state


def execute_node(state: OverallStateModel) -> OverallStateModel:
    """plan_node 에서 만들어진 subtasks 를 실행"""
    return state


def evaluate_node(state: OverallStateModel) -> OverallStateModel:
    """execute_node 에서 만들어진 결과를 평가"""
    return state


def replan_node(state: OverallStateModel) -> OverallStateModel:
    """evaluate_node 에서 평가 결과가 부정확할 경우 재계획"""
    return state


def output_node(state: Dict) -> OutputState:
    """최종 결과물 생성"""
    return state
