from langgraph.graph import END, START, StateGraph

from langgraph.checkpoint.base import BaseCheckpointSaver

import os

from app.graph.configuration import Configuration as Config
from app.graph.base import BaseGraph
from configs import StackType, config
from app import logger
from app.graph.states import OverallState, InputState, OutputState
from app.graph.nodes import (
    apreprocess_node,
    plan_node,
    to_output_node,
    embedding_node,
    retrieve_node,
    execute_node,
    evaluate_node,
    output_node,
    replan_node,
    should_replan,
)
from app.graph.schema import Deps
from functools import partial


class MapSearchGraph(BaseGraph):
    def __init__(self, deps: Deps, checkpointer: BaseCheckpointSaver):
        self.deps = deps
        super().__init__(checkpointer)

        if config.stack_type == StackType.LOCAL:
            # Save graph image in the graphs folder
            graph_dir = os.path.dirname(os.path.abspath(__file__))
            os.makedirs(graph_dir, exist_ok=True)
            filename = os.path.join(graph_dir, "graph.png")
            with open(filename, "wb") as f:
                f.write(self.compiled_graph.get_graph().draw_mermaid_png())
            logger.info(f"Graph image saved as {filename}")

    # Plan-Execute-Evaluate-Replan 워크플로우 (map-search-agent 패턴)
    def create_graph(self) -> StateGraph:
        workflow = StateGraph(
            OverallState,
            input_schema=InputState,
            output_schema=OutputState,
            config_schema=Config,
        )

        # 모든 노드 추가 (map-search-agent의 노드 구성 참고)
        workflow.add_node("plan", partial(plan_node, deps=self.deps))
        workflow.add_node("embedding", partial(embedding_node, deps=self.deps))
        workflow.add_node("retrieve", partial(retrieve_node, deps=self.deps))
        workflow.add_node("execute", partial(execute_node, deps=self.deps))
        workflow.add_node("evaluate", partial(evaluate_node, deps=self.deps))
        workflow.add_node("replan", partial(replan_node, deps=self.deps))
        workflow.add_node("output", partial(output_node, deps=self.deps))

        # 초기 플로우: 준비 단계 (map-search-agent의 preparation flow)
        workflow.add_edge(START, "plan")
        workflow.add_edge("plan", "embedding")
        workflow.add_edge("embedding", "retrieve")
        workflow.add_edge("retrieve", "execute")
        
        # 실행 루프: execute → evaluate (map-search-agent의 main loop)
        workflow.add_edge("execute", "evaluate")
        
        # 조건부 분기: 평가 결과에 따른 라우팅 (map-search-agent의 conditional routing)
        workflow.add_conditional_edges(
            "evaluate",
            should_replan,
            {
                "replan": "replan",    # 재계획 후 재실행
                "output": "output"     # 성공 또는 재시도 한계시 종료
            }
        )
        
        # 재계획 루프: replan → execute (map-search-agent의 retry loop)
        workflow.add_edge("replan", "execute")
        
        # 최종 종료
        workflow.add_edge("output", END)
        
        return workflow
