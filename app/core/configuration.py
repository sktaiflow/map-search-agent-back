"""Define the configurable parameters for the agent."""

from __future__ import annotations

from dataclasses import dataclass, fields, field
from typing import Optional, List

from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    # Changeme: Add configurable values here!
    # these values can be pre-set when you
    # create assistants (https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/)
    # and when you invoke the graph
    embdding_kwargs: dict = field(default_factory=dict)
    llm_model: str = "gpt-4o"
    version: str = "map-v1.0"
    # temperature: int = 0
    # streaming: bool = False

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        configurable = (config.get("configurable") or {}) if config else {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})
