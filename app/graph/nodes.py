from typing import Dict, Any, List
from app.graph.states import OverallState, OutputState, InputState
from app.graph.configuration import Configuration as Config
from app.core.prompts import PLANNING_TEMPLATE, PLANNING_PROMPT
from app.graph.schema import Deps
import utils.json as json
from utils.timezone import KST
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from langchain.output_parsers import PydanticOutputParser
from app.graph.schema import Plan


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
    from app.models.vectorstore.semantic_retrieval import SemanticSearchModel

    async with deps.postgres_db.get_async_session() as session:
        retrieved_examples: list[tuple[SemanticSearchModel, float]] = await deps.pgvector_models[
            0
        ].asearch_by_vector(session=session, embedding=query_embedding, similarity_cutoff=0.0)

    retrived_examples = []
    for few_shot_example, score in retrieved_examples:
        retrived_examples.append(
            {
                "query": few_shot_example.query,
                "cypher_query": few_shot_example.cypher_query,
                "score": score,
            }
        )
    return {"fewshot_examples": retrived_examples}


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
        user_id=state.user_id,
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


def execute_node(state: OverallState) -> OverallState:
    """plan_node 에서 만들어진 subtasks 를 실행"""
    return state


def evaluate_node(state: OverallState) -> OverallState:
    """execute_node 에서 만들어진 결과를 평가"""
    return state


def replan_node(state: OverallState) -> OverallState:
    """evaluate_node 에서 평가 결과가 부정확할 경우 재계획"""
    return state


def output_node(state: Dict) -> OutputState:
    """최종 결과물 생성"""
    return state
