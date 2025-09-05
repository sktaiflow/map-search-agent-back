from typing import Any, List, Type, Optional

from langchain_core.tools import BaseTool, ArgsSchema
from pydantic import BaseModel, Field

from app.schemas.map.plan import AddOnSubscriptions, AddOnDetailSubscriptions, AddOnHistory
from app.clients.map import MAPClient
from app.core.tools.utils import SafeValidationTool
from app.core.tools.map.base import MAPBaseToolKit
from configs import config as global_config
from configs.default import BaseConfig
from app import logger


class UserIdInput(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")


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


class PlanToolKit(MAPBaseToolKit):
    """요금제 관련 도구들을 관리하는 툴킷 -> method_api_key 공유하는 도구만 모아둬야함"""

    name: str = "PlanToolKit"
    description: str = "Plan 관련 도구들을 관리하는 툴킷 method_api_key 공유하는 도구만 모아둬야함"
    cfg: BaseConfig = global_config

    def __init__(self, map_client):
        super().__init__(map_client)

        try:
            self.method_api_key = self._verify_method_api_key()

        except KeyError as e:
            logger.error(
                type="tool",
                message=f"Method api key for {self.name} not found. Please check the config",
                exc_info=e,
            )
            raise

    def _verify_method_api_key(self) -> str:
        method_api_key = self.cfg.map_method_api_keys.get(self.name, None)
        if not method_api_key:
            raise KeyError(f"Method api key for {self.name} not found in config")
        return method_api_key

    def tools(self) -> List[SafeValidationTool]:
        raise NotImplementedError("This method is not implemented")

    def valid_tools(self) -> List[SafeValidationTool]:
        """사용 가능한 tool 반환 - 필요시에만 생성"""
        all_tools = [
            GetPlanAddOnAddOnSubscriptionsTool(
                map_client=self.map_client, method_api_key=self.method_api_key
            ),
            GetPlanAddOnSubscriptionsTool(
                map_client=self.map_client, method_api_key=self.method_api_key
            ),
            GetPlanAddOnHistoriesTool(
                map_client=self.map_client, method_api_key=self.method_api_key
            ),
        ]
        return [tool for tool in all_tools if tool.status]
