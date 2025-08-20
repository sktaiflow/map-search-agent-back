from langgraph.graph import END, START, StateGraph

from langgraph.checkpoint.base import BaseCheckpointSaver

import os

from app.core.graph.configuration import Configuration as Config
from app.core.graph.base import BaseGraph
from configs import StackType, config
from app import logger
from app.core.graph.state import OverallState, InputState, OutputState
from app.core.graph.nodes import (
    preprocess_node,
    plan_node,
    execute_node,
    evaluate_node,
    output_node,
    replan_node,
)


class MapSearchGraph(BaseGraph):
    def __init__(self, checkpointer: BaseCheckpointSaver):
        super().__init__(checkpointer)

        if config.stack_type == StackType.LOCAL:
            # Save graph image in the graphs folder
            graph_dir = os.path.dirname(os.path.abspath(__file__))
            os.makedirs(graph_dir, exist_ok=True)
            filename = os.path.join(graph_dir, "graph.png")

            with open(filename, "wb") as f:
                f.write(self.compiled_graph.get_graph().draw_mermaid_png())
            logger.info(f"Graph image saved as {filename}")

    def create_graph(self) -> StateGraph:
        workflow = StateGraph(
            OverallState,
            input_schema=InputState,
            output_schema=OutputState,
            config_schema=Config,
        )

        workflow.add_node("preprocess", preprocess_node)
        workflow.add_node("plan", plan_node)
        workflow.add_node("execute", execute_node)
        workflow.add_edge("final_answer", END)
