from abc import abstractmethod

from langgraph.graph.state import StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver


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
