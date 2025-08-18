from typing import Any, List, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.schemas.map.plan import AddOnSubscriptions, 
from app.clients.map import MAPClient


class UserIdInput(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")


class GetPlanAddOnAddOnSubscriptionsTool(BaseTool):
    name: str = "get_plan_add_on_add_on_subscriptions"
    description: str = "가입중인 부가서비스 목록을 조회한다."
    args_schema: Type[BaseModel] = UserIdInput
    map_client: MAPClient
    method_api_key: str

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"plan/add-on_{self.method_api_key}/add-on-subscriptions"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return AddOnSubscriptions.model_validate(response).model_dump()
