from app.schemas.map.contract import MobileContractDevice
from app.clients.map import MAPClient
from langchain_core.tools import BaseTool
from app.core.tools.map.base import SafeValidationTool
from pydantic import BaseModel, Field
from typing import Type


class UserIdInput(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")


# TODO: respone HttpBaseClientResponse 로 변경


class GetContractMobileContractDevicesTool(SafeValidationTool):
    name: str = "get_contract_mobile_contract_devices"
    description: str = "무선 회선에 대한 기본 가입정보를 조회한다."
    args_schema: Type[BaseModel] = UserIdInput
    response_model: Type[BaseModel] = MobileContractDevice

    def __init__(self, map_client: MAPClient, method_api_key: str):
        self.map_client = map_client
        self.method_api_key = method_api_key

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/devices"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return self._validate_response(response)


class GetPlanAddOnAddOnSubscriptionsTool(SafeValidationTool):
    name: str = "get_plan_add_on_add_on_subscriptions"
    description: str = "가입중인 부가서비스 목록을 조회한다."
    args_schema: Type[BaseModel] = UserIdInput
    response_model: Type[BaseModel] = AddOnSubscriptions

    def __init__(self, map_client: MAPClient, method_api_key: str):
        self.map_client = map_client
        self.method_api_key = method_api_key

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"plan/add-on_{self.method_api_key}/add-on-subscriptions"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return self._validate_response(response)
