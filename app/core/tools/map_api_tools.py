"""
MAP API 툴들 - StandardizedTool 기반으로 구현

사용자 계약 정보, 가입 상품, 요금제 가입 가능성 등을 MAP API를 통해 조회하는 툴들
"""

from typing import Any, Dict, List, Type
from pydantic import BaseModel

from app.clients.map import MAPClient
from app.core.tools.base import StandardizedTool
from app.schemas.map import (
    UserIdInput,
    PlanSubscriptionPreviewInput,
    MobileService,
    AddOnDetailSubscriptions,
    PlanSubscriptionPreview,
)


class GetContractServicesTool(StandardizedTool):
    """서비스/청구/고객 정보 조회 툴"""

    name: str = "get_contract_services"
    description: str = (
        "서비스관리번호별 서비스/청구/고객 정보를 조회합니다. "
        "SKT 회선이 아닌 경우 빈 객체를 반환합니다."
    )
    args_schema: Any = UserIdInput
    response_model: Any = MobileService
    status: bool = True

    # 의존성 주입될 컴포넌트들
    map_client: MAPClient
    method_api_key: str

    async def _arun(self, user_id: str, tool_select_reason: str = "") -> Dict[str, Any]:
        """
        고객의 서비스/청구/고객 정보 조회

        Args:
            user_id: 고객아이디 (서비스관리번호)
            tool_select_reason: 도구 선택 이유 (예: 고객의 연령을 확인하기 위해)

        Returns:
            고객 정보 조회 결과
        """
        try:
            endpoint = f"contract/mobile-contract_{self.method_api_key}/services"
            response = await self.map_client._request(
                "GET", endpoint, params={"svcMgmtNum": user_id}
            )
            response_data = response.json()
            return self._validate_response(response_data)

        except Exception as e:
            return {"error": f"고객 정보 조회 실패: {str(e)}", "user_id": user_id}


class GetPlanSubscriptionsTool(StandardizedTool):
    """가입된 상품 목록 조회 툴"""

    name: str = "get_plan_subscriptions"
    description: str = (
        "고객 기준으로 최대 10개 회선에 대해 가입된 모든 상품 목록을 조회합니다. "
        "현재 이용 중인 요금제와 부가서비스를 확인할 수 있습니다."
    )
    args_schema: Any = UserIdInput
    response_model: Any = List[AddOnDetailSubscriptions]
    status: bool = True

    # 의존성 주입될 컴포넌트들
    map_client: MAPClient
    method_api_key: str

    async def _arun(self, user_id: str, tool_select_reason: str = "") -> Dict[str, Any]:
        """
        고객의 가입 상품 목록 조회

        Args:
            user_id: 고객아이디 (서비스관리번호)
            tool_select_reason: 도구 선택 이유 (예: 고객의 현재 요금제를 확인하기 위해)

        Returns:
            가입 상품 목록 조회 결과
        """
        try:
            endpoint = f"plan/add-on_{self.method_api_key}/subscriptions"
            response = await self.map_client._request(
                "GET", endpoint, params={"svcMgmtNum": user_id}
            )
            response_data = response.json()
            return self._validate_response(response_data)

        except Exception as e:
            return {"error": f"가입 상품 조회 실패: {str(e)}", "user_id": user_id}


class CheckPlanEligibilityTool(StandardizedTool):
    """요금제 가입 가능성 조회 툴"""

    name: str = "check_plan_eligibility"
    description: str = (
        "기본요금제 가입가능여부 및 가입불가사유를 조회합니다. "
        "단말기 키워드가 입력되는 경우는 기변으로 간주하여 처리하되 "
        "키워드와 유사한 단말 정보가 없는 경우는 에러로 반환합니다."
    )
    args_schema: Any = PlanSubscriptionPreviewInput
    response_model: Any = PlanSubscriptionPreview
    status: bool = True

    # 의존성 주입될 컴포넌트들
    map_client: MAPClient
    method_api_key: str

    async def _arun(
        self, user_id: str, prod_id: str, tool_select_reason: str = ""
    ) -> Dict[str, Any]:
        """
        요금제 가입 가능성 조회

        Args:
            user_id: 고객아이디 (서비스관리번호)
            prod_id: 상품아이디
            tool_select_reason: 도구 선택 이유 (예: 고객이 특정 요금제에 가입 가능한지 확인하기 위해)

        Returns:
            요금제 가입 가능성 조회 결과
        """
        try:
            endpoint = (
                f"plan/basic-plan_{self.method_api_key}/plan-subscription-previews"
            )
            response = await self.map_client._request(
                "GET", endpoint, params={"svcMgmtNum": user_id, "prodId": prod_id}
            )
            response_data = response.json()
            return self._validate_response(response_data)

        except Exception as e:
            return {
                "error": f"요금제 가입 가능성 조회 실패: {str(e)}",
                "user_id": user_id,
                "prod_id": prod_id,
            }
