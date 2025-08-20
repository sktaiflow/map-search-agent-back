"""Define the configurable parameters for the agent."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from dataclasses import dataclass, fields, field

from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    embedding_kwargs: dict = field(default_factory=dict)
    llm_model: str = "gpt-4o"
    version: str = "map-v1.0"
    temperature: float = 0.0
    streaming: bool = False

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        configurable = (config.get("configurable") or {}) if config else {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})
