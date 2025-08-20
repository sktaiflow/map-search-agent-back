from app.core.agents import BaseAgent, BaseAgentConfig
from app.core.graph import BaseGraph


class MapSearchAgentConfig(BaseAgentConfig):
    agent_name: str = "map-search-agent"


class MapSearchAgent(BaseAgent):
    config = MapSearchAgentConfig()

    def __init__(self, graph: BaseGraph) -> None:
        super().__init__(graph)