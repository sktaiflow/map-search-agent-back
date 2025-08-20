from app.agents.base import BaseAgent, BaseAgentConfig
from typing import Any
from app.schemas.chat import ChatMessage


class MapSearchAgentConfig(BaseAgentConfig):
    pass


class MapSearchAgent(BaseAgent):
    config = MapSearchAgentConfig(agent_name="map-search-agent")

    async def postprocess_messages(self, content: dict[str, Any]):
        answer = content.get("answer", "")
        return ChatMessage(type="ai", content=answer)
