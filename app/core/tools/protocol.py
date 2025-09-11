from typing import TypeVar, Sequence, Protocol, Generic, runtime_checkable

ToolT = TypeVar("ToolT", covariant=True)


@runtime_checkable
class ToolKitCollectorProtocol(Protocol, Generic[ToolT]):
    """모든 Toolkit이 따라야 하는 최소 인터페이스."""

    @property
    def get_tools_description(self) -> str: ...

    @property
    def get_valid_tools(self) -> Sequence[ToolT]: ...

    @property
    def get_valid_tools_with_openai_function(self) -> Sequence[ToolT]: ...
