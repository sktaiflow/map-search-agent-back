from app.schemas.map.contract import MobileContractDevice
from app.clients.map import MAPClient
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class UserIdInput(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")


class GetContractMobileContractDevicesTool(BaseTool):
    name: str = "get_contract_mobile_contract_devices"
    description: str = "무선 회선에 대한 기본 가입정보를 조회한다."
    args_schema: Type[BaseModel] = UserIdInput
    map_client: MAPClient
    method_api_key: str

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/devices"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return MobileContractDevice.model_validate(response).model_dump()
