from langchain_core.tools import BaseTool
from typing import List
from app.core.tools.utils import get_tools_description
from abc import ABC, abstractmethod


class MAPBaseToolKit(ABC):
    """map api 도구들을 관리하는 기본 툴킷 클래스"""

    def __init__(self, map_client, method_api_key: str, status: bool = True):
        self.map_client = map_client
        self.method_api_key = method_api_key
        self.status = status

    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """모든 tool 반환"""

    @abstractmethod
    def get_valid_tools(self) -> List[BaseTool]:
        """사용 가능한 tool 반환"""
