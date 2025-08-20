from langchain_core.runnables import RunnableConfig
from ..graph.state import OverallState


# TODO: query: list[str] 전처리 방식 추가 (현재 ',''.join)
def replace_query_with_synonym(state: OverallState, config: RunnableConfig) -> dict[str, str]:
    """
    쿼리를 동의어로 변환
    프로세스:
        1. 쿼리를 키워드로 분리
        2. 분리된 키워드 -> C & C API 호출
        3. SCORE 기반 비교 후 -> 원본쿼리 변환
    """
    query = ",".join(state.query)

    return {"query_synonym": query}


async def a_replace_query_with_synonym(
    state: OverallState, config: RunnableConfig
) -> dict[str, str]:
    """
    쿼리를 동의어로 변환
    프로세스:
        1. 쿼리를 키워드로 분리
        2. 분리된 키워드 -> C & C API 호출
        3. SCORE 기반 비교 후 -> 원본쿼리 변환
    """
    query = ",".join(state.query)
    return {"query_synonym": query}
