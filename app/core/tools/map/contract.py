from app.schemas.map.contract import (
    MobileContractDevice,
    ContractRemainInfo,
    NoContractPoint,
    DeviceContract,
    MobileService,
)
from app.schemas.map.plan import AddOnSubscriptions
from app.clients.map import MAPClient
from langchain_core.tools import ArgsSchema, BaseTool
from app.core.tools.map.base import SafeValidationTool
from pydantic import BaseModel, Field
from typing import Type
from typing import List

from app.core.tools.map.base import BaseToolKit


class UserIdInput(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")


# TODO: respone HttpBaseClientResponse 로 변경


class GetContractMobileContractDevicesTool(SafeValidationTool):
    name: str = "get_contract_mobile_contract_devices"
    description: str = "무선 회선에 대한 기본 가입정보를 조회한다."
    args_schema: ArgsSchema | None = UserIdInput
    response_model: Type[BaseModel] = MobileContractDevice
    map_client: MAPClient
    method_api_key: str
    status: bool = True

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/devices"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        response_data = response.json()
        if isinstance(response_data, dict):
            return self._validate_response(response_data)
        else:
            return {"data": response_data}


class GetContractMobileContractRemainedContractsTool(SafeValidationTool):
    name: str = "get_contract_mobile_contract_remained_contracts"
    description: str = (
        "무선 회선에 가입된 약정 상세를 조회한다. 단말할부금 유무를 조회한다, 선택약정, T지원금약정, 요금약정, 약정위약금2 등  약정상품 별 가입/승계여부를 확인하고 가입중인 약정은 상세 내용을 조회한다, 최근 2년 내 종료된 할부/약정 등의 유무를 조회한다. , 사용 가능한 무약정포인트 유무를 조회한다."
    )
    args_schema: ArgsSchema | None = UserIdInput
    map_client: MAPClient
    method_api_key: str
    response_model: Type[BaseModel] = ContractRemainInfo
    status: bool = False

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/remained-contracts"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return self._validate_response(response)


class GetContractMobileContractNoContractPointsTool(SafeValidationTool):
    name: str = "get_contract_mobile_contract_no_contract_points"
    description: str = "무약정 플랜 포인트 상세 정보를 조회한다."
    args_schema: ArgsSchema | None = UserIdInput
    map_client: MAPClient
    method_api_key: str
    response_model: Type[BaseModel] = NoContractPoint
    status: bool = False

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/no-contract-points"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return self._validate_response(response)


class GetContractMobileContractDeviceContractsTool(SafeValidationTool):
    name: str = "get_contract_mobile_contract_device_contracts"
    description: str = (
        "무선 회선 기준 구매/약정 정보를 조회한다., 가입유형(신규/기변 등), 가입일자 조회, T지원금약정/선택약정/다이렉트플랜 조회 등"
    )
    args_schema: ArgsSchema | None = UserIdInput
    map_client: MAPClient
    method_api_key: str
    response_model: Type[BaseModel] = DeviceContract
    status: bool = False

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/device-contracts"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return self._validate_response(response)


class GetContractMobileContractServicesTool(SafeValidationTool):
    name: str = "get_contract_mobile_contract_services"
    description: str = (
        "서비스관리번호별 서비스/청구/고객 정보를 조회한다, SKT 회선이 아닌 경우 빈 오브젝트({}) 리턴한다."
    )
    args_schema: ArgsSchema | None = UserIdInput
    map_client: MAPClient
    method_api_key: str
    response_model: Type[BaseModel] = MobileService
    status: bool = False

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/services"
        response = await self.map_client._request("GET", endpoint, params={"svcMgmtNum": user_id})
        return self._validate_response(response)


class ContractToolKit(BaseToolKit):
    """contract 관련 도구들을 관리하는 툴킷 method_api_key 공유하는 도구만 모아둬야함"""

    def get_tool_class(self) -> List[Type[BaseTool]]:
        return [
            GetContractMobileContractDevicesTool,
            GetContractMobileContractRemainedContractsTool,
            GetContractMobileContractNoContractPointsTool,
            GetContractMobileContractDeviceContractsTool,
            GetContractMobileContractServicesTool,
        ]

    def get_tools(self) -> List[BaseTool]:
        """contract 관련 도구들을 반환합니다."""
        return [
            GetContractMobileContractDevicesTool(
                map_client=self.map_client, method_api_key=self.method_api_key, status=True
            ),
            GetContractMobileContractRemainedContractsTool(
                map_client=self.map_client, method_api_key=self.method_api_key, status=False
            ),
            GetContractMobileContractNoContractPointsTool(
                map_client=self.map_client, method_api_key=self.method_api_key, status=False
            ),
            GetContractMobileContractDeviceContractsTool(
                map_client=self.map_client, method_api_key=self.method_api_key, status=False
            ),
            GetContractMobileContractServicesTool(
                map_client=self.map_client, method_api_key=self.method_api_key, status=False
            ),
        ]
