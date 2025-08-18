from abc import abstractmethod

from langgraph.graph.state import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

import os

from .configuration import Configuration as Config
from configs import StackType, config
from utils.logger import logger
from .state import OverallStateModel, InputState, OutputState
from .nodes import init_node, plan_node, execute_node, evaluate_node, output_node, replan_node


class BaseGraph:
    """
    LangGraph 를 정의하기 위한 BaseGraph
    """

    def __init__(self, checkpointer: BaseCheckpointSaver):
        self.graph = self.create_graph()
        self.compiled_graph = self.graph.compile()

    @abstractmethod
    def create_graph(self) -> StateGraph:
        """각 Graph에서 구현해야 할 메서드"""
        raise NotImplementedError("create_graph() is required to be implemented in each subclass.")


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
            OverallStateModel, input=InputState, output=OutputState, config_schema=Config
        )

        ## 노드 추가

        workflow.add_node("init", init_node)
        workflow.add_node("plan", plan_node)
        workflow.add_node("execute", execute_node)
        workflow.add_node("evaluate", evaluate_node)
        workflow.add_node("output", output_node)
        workflow.add_node("replan", replan_node)

        ## 조건부 노드 추가
        workflow.add_conditional_edges(
            "agent",
            replan_or_finish,  # 이 함수가 "final_response" 또는 "planner"를 반환
            {
                "final_response": "final_response",  # ✅ 최종 응답 노드로 이동
                "planner": "planner",  # 재계획으로 이동
            },
        )

        ## edge 추가

        workflow.add_edge(workflow.get_node("init"), workflow.get_node("plan"))
        workflow.add_edge(workflow.get_node("plan"), workflow.get_node("execute"))
        workflow.add_edge(workflow.get_node("execute"), workflow.get_node("evaluate"))
