from typing import Any, List, Type

from langchain_core.tools import BaseTool, ArgsSchema
from pydantic import BaseModel, Field

from app.schemas.map.plan import AddOnSubscriptions, AddOnDetailSubscriptions, AddOnHistory
from app.clients.map import MAPClient
from app.core.tools.map.base import SafeValidationTool
from app.core.tools.map.base import BaseToolKit


class UserIdInput(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")


# TODO: respone HttpBaseClientResponse 로 변경


class GetPlanAddOnAddOnSubscriptionsTool(SafeValidationTool):
    name: str = "get_plan_add_on_add_on_subscriptions"
    description: str = "가입중인 부가서비스 목록을 조회한다."
    args_schema: ArgsSchema | None = UserIdInput
    response_model: Type[BaseModel] = AddOnSubscriptions
    map_client: MAPClient
    method_api_key: str
    status: bool = True

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"plan/add-on_{self.method_api_key}/add-on-subscriptions"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        response_data = response.json()
        return self._validate_response(response_data)


class GetPlanAddOnSubscriptionsTool(SafeValidationTool):
    name: str = "get_plan_add_on_subscriptions"
    description: str = "고객 기준으로 최대 10개 회선에 대해 가입된 모든 상품 목록을 조회한다."
    args_schema: ArgsSchema | None = UserIdInput
    map_client: MAPClient
    method_api_key: str
    response_model: Type[Any] = List[AddOnDetailSubscriptions]
    status: bool = False

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> list:
        endpoint = f"plan/add-on_{self.method_api_key}/subscriptions"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return self._validate_response(response)


class GetPlanAddOnHistoriesTool(SafeValidationTool):
    name: str = "get_plan_add_on_histories"
    description: str = "서비스 기준으로 상품/할인 가입이력을 조회한다."
    args_schema: ArgsSchema | None = UserIdInput
    map_client: MAPClient
    method_api_key: str
    response_model: Type[BaseModel] = AddOnHistory
    status: bool = False

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"plan/add-on_{self.method_api_key}/histories"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return self._validate_response(response)


class PlanToolKit(BaseToolKit):
    """요금제 관련 도구들을 관리하는 툴킷 -> method_api_key 공유하는 도구만 모아둬야함"""

    def get_tool_class(self) -> List[Type[BaseTool]]:
        return [
            GetPlanAddOnAddOnSubscriptionsTool,
            GetPlanAddOnSubscriptionsTool,
            GetPlanAddOnHistoriesTool,
        ]

    def get_tools(self) -> List[BaseTool]:
        """요금제 관련 도구들을 반환합니다."""
        return [
            GetPlanAddOnAddOnSubscriptionsTool(
                map_client=self.map_client, method_api_key=self.method_api_key, status=True
            ),
            GetPlanAddOnSubscriptionsTool(
                map_client=self.map_client, method_api_key=self.method_api_key, status=False
            ),
            GetPlanAddOnHistoriesTool(
                map_client=self.map_client, method_api_key=self.method_api_key, status=False
            ),
        ]
