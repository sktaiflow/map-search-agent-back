from app.schemas.map.contract import (
    MobileContractDevice,
    ContractRemainInfo,
    NoContractPoint,
    DeviceContract,
    MobileService,
)
from app.clients.map import MAPClient
from langchain_core.tools import ArgsSchema
from app.core.tools.utils import SafeValidationTool
from pydantic import BaseModel, Field
from typing import Type
from typing import List

from app.core.tools.map.base import MAPBaseToolKit
from configs import config as global_config
from configs.default import BaseConfig
from app import logger


class UserIdInput(BaseModel):
    user_id: str = Field(description="고객아이디 (혹은 서비스관리번호- SvcMgmtNum)")


# TODO: 필요시 responeFormat -> HttpBaseClientResponse 로 변경
class GetContractMobileContractDevicesTool(SafeValidationTool):
    name: str = "get_contract_mobile_contract_devices"
    description: str = "고객에 대한 기본 정보(나이, 성별, 가입 정보 등)를 조회한다."
    args_schema: ArgsSchema | None = UserIdInput
    response_model: Type[BaseModel] = MobileContractDevice
    map_client: MAPClient
    method_api_key: str
    status: bool = True

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/devices"
        response = await self.map_client._request(
            "GET", endpoint, params={"svcMgmtNum": user_id}
        )
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
        response = await self.map_client._request(
            "GET", endpoint, params={"svcMgmtNum": user_id}
        )
        response_data = response.json()
        return self._validate_response(response_data)


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
        response = await self.map_client._request(
            "GET", endpoint, params={"svcMgmtNum": user_id}
        )
        response_data = response.json()
        return self._validate_response(response_data)


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
        response = await self.map_client._request(
            "GET", endpoint, params={"svcMgmtNum": user_id}
        )
        return self._validate_response(response)


class GetContractMobileContractServicesTool(SafeValidationTool):
    name: str = "get_contract_mobile_contract_services"
    description: str = (
        "서비스관리번호별 서비스/청구/고객 정보를 조회한다, SKT 회선이 아닌 경우 빈 오브젝트({}) 리턴한다."
    )
    args_schema: ArgsSchema | None = UserIdInput
    response_model: Type[BaseModel] = MobileService
    map_client: MAPClient
    method_api_key: str
    status: bool = False

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support sync execution.")

    async def _arun(self, user_id: str) -> dict:
        endpoint = f"contract/mobile-contract_{self.method_api_key}/services"
        response = await self.map_client._request(
            "GET", endpoint, params={"svcMgmtNum": user_id}
        )
        return self._validate_response(response)


class ContractToolKit(MAPBaseToolKit):
    """contract 관련 도구들을 관리하는 툴킷 method_api_key 공유하는 도구만 모아둬야함"""

    name: str = "ContractToolKit"
    description: str = (
        "contract 관련 도구들을 관리하는 툴킷 method_api_key 공유하는 도구만 모아둬야함"
    )
    cfg: BaseConfig = global_config

    def __init__(self, map_client: MAPClient):
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
        method_api_key = self.cfg.map_method_api_keys.get(self.name.lower(), None)
        if not method_api_key:
            raise KeyError(f"Method api key for {self.name} not found in config")
        return method_api_key

    def tools(self) -> List[SafeValidationTool]:
        raise NotImplementedError("This method is not implemented")

    def valid_tools(self) -> List[SafeValidationTool]:
        """사용 가능한 tool 반환 - 필요시에만 생성"""
        all_tools = [
            GetContractMobileContractDevicesTool(
                map_client=self.map_client, method_api_key=self.method_api_key
            ),
            GetContractMobileContractRemainedContractsTool(
                map_client=self.map_client, method_api_key=self.method_api_key
            ),
            GetContractMobileContractNoContractPointsTool(
                map_client=self.map_client, method_api_key=self.method_api_key
            ),
            GetContractMobileContractDeviceContractsTool(
                map_client=self.map_client, method_api_key=self.method_api_key
            ),
            GetContractMobileContractServicesTool(
                map_client=self.map_client, method_api_key=self.method_api_key
            ),
        ]
        return [tool for tool in all_tools if tool.status]
