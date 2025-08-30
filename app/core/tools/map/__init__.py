from app.core.tools.map.contract import ContractToolKit
from app.core.tools.map.plan import PlanToolKit

from typing import Any, Dict, List
from langchain.tools import BaseTool  # 가정
from app.core.tools.map.base import BaseToolKit
from langchain_core.utils.function_calling import convert_to_openai_function


class MAPTools:
    _TOOLKIT_CLASSES = [ContractToolKit, PlanToolKit]

    def __init__(self, map_client, method_api_key: Dict[str, str]):
        self.map_client = map_client
        self.method_api_key = method_api_key

    def get_toolkit(self) -> List[BaseToolKit]:
        """toolkit 클래스 반환"""
        return [
            toolkit_class(self.map_client, self.method_api_key[toolkit_class.__name__])
            for toolkit_class in self._TOOLKIT_CLASSES
        ]

    def get_valid_tools(self) -> List[BaseTool]:
        """toolkit_classes 안 모든 tool 반환"""
        all_tools = []
        for toolkit in self.get_toolkit():  # 오타 수정
            all_tools.extend(toolkit.get_tools())
        return [tool for tool in all_tools if tool.status]

    def get_valid_tools_with_openai_function(self) -> List[dict]:
        """toolkit_classes 안 모든 tool을 openai function 형식으로 반환"""
        return [convert_to_openai_function(tool) for tool in self.get_valid_tools()]

    def __len__(self) -> int:
        return len(self.get_valid_tools())

    def get_tools_description(self) -> str:
        """toolkit 클래스 이름 설명 반환"""
        return "\n".join([f"{tools.name}: {tools.description}" for tools in self.get_valid_tools()])


__all__ = ["MAPTools"]
