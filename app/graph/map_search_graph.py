from langgraph.graph import END, START, StateGraph

from langgraph.checkpoint.base import BaseCheckpointSaver

import os

from app.graph.configuration import Configuration as Config
from app.graph.base import BaseGraph
from configs import StackType, config
from app import logger
from app.graph.states import OverallState, InputState, OutputState
from app.graph.nodes import (
    plan_node,
    execute_node,
    evaluate_node,
    output_node,
    replan_node,
    next_action_after_replan,
)
from app.graph.schema import Deps
from functools import partial


class MapSearchGraph(BaseGraph):
    def __init__(self, deps: Deps, checkpointer: BaseCheckpointSaver):
        self.deps = deps
        super().__init__(checkpointer)

        # if config.stack_type == StackType.LOCAL:
        # Save graph image in the graphs folder
        # graph_dir = os.path.dirname(os.path.abspath(__file__))
        # os.makedirs(graph_dir, exist_ok=True)
        # filename = os.path.join(graph_dir, "graph.png")
        # with open(filename, "wb") as f:
        #     f.write(self.compiled_graph.get_graph().draw_mermaid_png())
        # logger.info(f"Graph image saved as {filename}")

    # TODO 노트 병렬쳐리 (start -> plan, embeding)
    def create_graph(self) -> StateGraph:
        workflow = StateGraph(
            OverallState,
            input_schema=InputState,
            output_schema=OutputState,
            config_schema=Config,
        )

        workflow.add_node("plan", partial(plan_node, deps=self.deps))
        workflow.add_node("execute", partial(execute_node, deps=self.deps))
        workflow.add_node("evaluate", partial(evaluate_node, deps=self.deps))
        workflow.add_node("replan", partial(replan_node, deps=self.deps))
        workflow.add_node("output", partial(output_node, deps=self.deps))

        workflow.add_edge(START, "plan")
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "evaluate")
        workflow.add_edge("evaluate", "replan")
        workflow.add_conditional_edges(
            "replan",
            next_action_after_replan,
            {
                "execute": "execute",
                "output": "output",
            },
        )
        workflow.add_edge("output", END)
        return workflow
