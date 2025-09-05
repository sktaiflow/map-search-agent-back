from app.core.tools.map.contract import ContractToolKit
from app.core.tools.map.plan import PlanToolKit

from typing import Any, Dict, List, Type, Optional
from app.core.tools.utils import SafeValidationTool
from app.core.tools.map.base import MAPBaseToolKit
from langchain_core.utils.function_calling import convert_to_openai_function
from app.core.tools.protocol import ToolKitCollectorProtocol


class MAPToolkitCollectors(ToolKitCollectorProtocol[SafeValidationTool]):
    """MAP Tool 집합 관리하는 Class"""

    _TOOLKIT_CLASSES: List[Type[MAPBaseToolKit]] = [ContractToolKit, PlanToolKit]

    def __init__(self, map_client):
        self.map_client = map_client

    def get_valid_tools(self) -> List[SafeValidationTool]:
        """사용 가능한 tool 반환"""
        valid_tool_list: List[SafeValidationTool] = []
        for toolkit_class in self._TOOLKIT_CLASSES:
            tools = toolkit_class(self.map_client).valid_tools()
            valid_tool_list.extend([tool for tool in tools if isinstance(tool, SafeValidationTool)])
        return valid_tool_list


__all__ = ["MAPToolkitCollectors"]
