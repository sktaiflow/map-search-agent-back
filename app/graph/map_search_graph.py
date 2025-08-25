from langgraph.graph import END, START, StateGraph

from langgraph.checkpoint.base import BaseCheckpointSaver

import os

from graph.configuration import Configuration as Config
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

    # TODO 노트 병렬쳐리 (start -> plan, embeding)
    def create_graph(self) -> StateGraph:
        workflow = StateGraph(
            OverallState,
            input_schema=InputState,
            output_schema=OutputState,
            config_schema=Config,
        )

        workflow.add_node("embedding", partial(embedding_node, deps=self.deps))
        workflow.add_node("retrieve", partial(retrieve_node, deps=self.deps))
        workflow.add_node("plan", partial(plan_node, deps=self.deps))
        workflow.add_node("to_output", to_output_node)
        workflow.add_edge(START, "embedding")
        workflow.add_edge("embedding", "retrieve")
        workflow.add_edge("retrieve", "plan")
        workflow.add_edge("plan", "to_output")
        workflow.add_edge("to_output", END)
        return workflow
