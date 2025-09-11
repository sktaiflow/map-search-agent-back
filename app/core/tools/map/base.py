from langchain_core.tools import BaseTool
from typing import List, Optional
from app.core.tools.utils import get_tools_description
from abc import ABC, abstractmethod


class MAPBaseToolKit(ABC):
    """map api 도구들을 관리하는 기본 툴킷 클래스"""

    def __init__(self, map_client):
        self.map_client = map_client

    @abstractmethod
    def tools(self) -> List[BaseTool]:
        """모든 tool 반환"""

    @abstractmethod
    def valid_tools(self) -> List[BaseTool]:
        """사용 가능한 tool 반환"""
