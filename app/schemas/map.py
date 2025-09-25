"""
MAP API 스키마 정의

MAP API와 관련된 모든 입력 및 응답 스키마를 정의합니다.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, RootModel


# =============================================================================
# 입력 스키마들
# =============================================================================
class ToolArgsBase(BaseModel):
    """툴 공통 입력 스키마"""

    tool_select_reason: str = Field(
        description="이 툴을 선택한 이유와 이 툴에서 얻고자 하는 결과값"
    )


class UserIdInput(ToolArgsBase):
    """사용자 ID 입력 스키마 (MAP API 공통)"""

    user_id: str = Field(description="고객아이디 (user_id, SvcMgmtNum)")


class PlanSubscriptionPreviewInput(ToolArgsBase):
    """요금제 가입 가능성 조회 입력 스키마"""

    user_id: str = Field(description="고객아이디 (user_id, SvcMgmtNum)")
    prod_id: str = Field(description="상품아이디 (legacyProductId, 상품코드매핑ID)")


# =============================================================================
# 응답 스키마들
# =============================================================================


class MobileService(BaseModel):
    """모바일 서비스 정보"""

    model_config = ConfigDict(
        populate_by_name=True,
    )

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_num: str = Field(..., alias="svcNum", description="서비스번호")
    svc_cd: str = Field(..., alias="svcCd", description="서비스구분코드")
    svc_st_cd: str = Field(..., alias="svcStCd", description="서비스상태코드")
    svc_st_chg_cd: str = Field(
        ..., alias="svcStChgCd", description="서비스상태변경코드"
    )
    svc_chg_rsn_cd: str = Field(
        ..., alias="svcChgRsnCd", description="서비스변경사유코드"
    )
    svc_typ_cd: str = Field(..., alias="svcTypCd", description="서비스이용종류코드")
    svc_scrb_dtm: str = Field(..., alias="svcScrbDtm", description="서비스가입일자")
    scrb_req_rsn_cd: str = Field(
        ..., alias="scrbReqRsnCd", description="가입신청사유코드"
    )
    wlf_dc_cd: str = Field(..., alias="wlfDcCd", description="복지할인유형코드")
    estation_agree_yn: str = Field(
        ..., alias="estationAgreeYn", description="웹회원신청동의여부"
    )
    fee_prod_id: str = Field(..., alias="feeProdId", description="요금상품ID")
    fee_prod_nm: str = Field(..., alias="feeProdNm", description="요금상품명")
    fee_prod_chg_dt: str = Field(
        ..., alias="feeProdChgDt", description="요금제변경일자"
    )
    eqp_mdl_cd: str = Field(..., alias="eqpMdlCd", description="단말기모델코드")
    eqp_mdl_nm: str = Field(..., alias="eqpMdlNm", description="단말기모델명")
    eqp_ser_num: str = Field(..., alias="eqpSerNum", description="단말기일련번호")
    eqp_usg_cd: str = Field(..., alias="eqpUsgCd", description="단말기용도코드")
    eqp_mthd_cd: str = Field(..., alias="eqpMthdCd", description="단말기방식코드")
    eqp_mktg_dt: str = Field(..., alias="eqpMktgDt", description="단말기출시일자")
    nw_mthd_cd: str = Field(..., alias="nwMthdCd", description="네트워크방식코드")
    cust_num: str = Field(..., alias="custNum", description="고객번호")
    cust_nm: str = Field(..., alias="custNm", description="고객명")
    ctz_corp_biz_num: str = Field(
        ..., alias="ctzCorpBizNum", description="주민번호/사업자등록번호"
    )
    ssn_birth_dt: str = Field(..., alias="ssnBirthDt", description="생년월일")
    ssn_sex_cd: str = Field(..., alias="ssnSexCd", description="성별코드")
    cust_typ_cd: str = Field(..., alias="custTypCd", description="고객유형코드")
    cust_dtl_typ_cd: str = Field(
        ..., alias="custDtlTypCd", description="고객세부유형코드"
    )
    age: str = Field(..., alias="age", description="고객나이")
    acnt_num: str = Field(..., alias="acntNum", description="계정번호")
    acnt_typ_cd: str = Field(..., alias="acntTypCd", description="계정유형코드")
    pay_mthd_cd: str = Field(..., alias="payMthdCd", description="납부방법코드")


class SubscriptionProduct(BaseModel):
    """가입 상품 요약 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    prod_nm: str = Field(..., alias="prodNm", description="상품명")
    svc_prod_cd: str = Field(
        ...,
        alias="svcProdCd",
        description="서비스상품구분코드 (1:기본요금제/2:부가요금제/3:부가서비스)",
    )
    scrb_dt: str = Field(..., alias="scrbDt", description="가입일자 (YYYYMMDD)")

    class Config:
        populate_by_name = True


class SubscriptionDiscount(BaseModel):
    """가입할인혜택목록"""

    dc_id: str = Field(..., alias="dcId", description="할인ID")
    dc_nm: str = Field(..., alias="dcNm", description="할인명")
    eff_sta_dtm: str = Field(
        ..., alias="effStaDtm", description="할인적용일시 (YYYYMMDDHH24miss)"
    )

    class Config:
        populate_by_name = True


class ContractServiceSummary(BaseModel):
    """서비스 관리 번호별 가입 상품/할인 요약"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_num: str = Field(..., alias="svcNum", description="서비스번호")
    twld_exps_yn: str = Field(..., alias="twldExpsYn", description="Tworld노출여부")
    scrb_prod_list: List[SubscriptionProduct] = Field(
        default_factory=list, alias="scrbProdList", description="가입상품목록"
    )
    scrb_dc_list: List[SubscriptionDiscount] = Field(
        default_factory=list, alias="scrbDcList", description="가입할인혜택목록"
    )

    class Config:
        populate_by_name = True


class ContractServiceSummaryList(RootModel[List[ContractServiceSummary]]):
    """서비스 관리 번호별 가입 상품/할인 요약의 목록"""

    pass


class SupplementaryPlan(BaseModel):
    """보조요금제 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    prod_nm: str = Field(..., alias="prodNm", description="상품명")
    bas_fee_amt: str = Field(..., alias="basFeeAmt", description="기본료금액")

    class Config:
        populate_by_name = True


class DiscountInfo(BaseModel):
    """할인 정보"""

    dc_id: str = Field(..., alias="dcId", description="할인ID")
    dc_nm: str = Field(..., alias="dcNm", description="할인명")
    eff_sta_dtm: str = Field(..., alias="effStaDtm", description="할인적용일시")

    class Config:
        populate_by_name = True


class AddOnDetailProduct(BaseModel):
    """부가서비스 상세 상품 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    prod_nm: str = Field(..., alias="prodNm", description="상품명")
    fix_amt_amt: str = Field(..., alias="fixAmtAmt", description="정액료금액")
    scrb_dc_list: List[DiscountInfo] = Field(
        default=[], alias="scrbDcList", description="가입할인목록"
    )

    class Config:
        populate_by_name = True


class AddOnDetailSubscriptions(BaseModel):
    """부가서비스 상세 가입정보"""

    add_on_cnt: str = Field(..., alias="addOnCnt", description="가입중부가서비스갯수")
    free_add_on_cnt: str = Field(
        ..., alias="freeAddOnCnt", description="가입중무료부가서비스갯수"
    )
    paid_add_on_cnt: str = Field(
        ..., alias="paidAddOnCnt", description="가입중유료부가서비스갯수"
    )
    free_add_on_list: List[AddOnDetailProduct] = Field(
        default=[], alias="freeAddOnList", description="무료부가서비스목록"
    )
    paid_add_on_list: List[AddOnDetailProduct] = Field(
        default=[], alias="paidAddOnList", description="유료부가서비스목록"
    )
    supl_plan_list: List[SupplementaryPlan] = Field(
        default=[], alias="suplPlanList", description="보조요금제목록"
    )
    smart_call_pick_list: List[AddOnDetailProduct] = Field(
        default=[], alias="smartCallPickList", description="스마트콜픽목록"
    )

    class Config:
        populate_by_name = True


class ProductInfo(BaseModel):
    """상품 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    prod_nm: str = Field(..., alias="prodNm", description="상품명")
    svc_prod_cd: str = Field(..., alias="svcProdCd", description="상품구분코드")

    class Config:
        populate_by_name = True


class PMProductInfo(BaseModel):
    """PM 상품 정보"""

    pm_product_id: str = Field(..., alias="pmProductId", description="PM상품ID")
    legacy_product_id: str = Field(
        ..., alias="legacyProductId", description="Legacy상품ID"
    )
    product_name: str = Field(..., alias="productName", description="상품명")

    class Config:
        populate_by_name = True


class PMCampaignInfo(BaseModel):
    """PM 캐페인 정보"""

    pm_campaign_id: str = Field(..., alias="pmCampaignId", description="PM혜택ID")
    campaign_name: str = Field(..., alias="campaignName", description="혜택명")

    class Config:
        populate_by_name = True


class ProductRelationError(BaseModel):
    """상품 연관 조건 미충족 목록"""

    pre_termination_required_product_list: List[PMProductInfo] = Field(
        default_factory=list,
        alias="preTerminationRequiredProductList",
        description="사전해지필요상품목록",
    )
    pre_signup_required_product_list: List[PMProductInfo] = Field(
        default_factory=list,
        alias="preSignupRequiredProductList",
        description="사전가입필요상품목록",
    )

    class Config:
        populate_by_name = True


class CampaignRelationError(BaseModel):
    """혜택 연관 조건 미충족 목록"""

    pre_termination_required_campaign_list: List[PMCampaignInfo] = Field(
        default_factory=list,
        alias="preTerminationRequiredCampaignList",
        description="사전해지필요혜택목록",
    )
    pre_signup_required_campaign_list: List[PMCampaignInfo] = Field(
        default_factory=list,
        alias="preSignupRequiredCampaignList",
        description="사전가입필요혜택목록",
    )

    class Config:
        populate_by_name = True


class BenefitInfo(BaseModel):
    """혜택 정보"""

    benefit_name: str = Field(..., alias="benefitName", description="혜택명")
    role: str = Field(..., alias="role", description="모두/선택제공여부")
    signup_status: str = Field(..., alias="signupStatus", description="가입상태")
    applied_status: str = Field(..., alias="appliedStatus", description="적용상태")
    next_plan_yn: str = Field(..., alias="nextPlanYN", description="유지/해지여부")

    class Config:
        populate_by_name = True


class CustomerBenefit(BaseModel):
    """고객 혜택 정보"""

    benefit_name: str = Field(..., alias="benefitName", description="혜택명")
    signup_status: str = Field(..., alias="signupStatus", description="가입상태")
    applied_status: str = Field(..., alias="appliedStatus", description="적용상태")
    next_plan_yn: str = Field(..., alias="nextPlanYN", description="유지/해지여부")

    class Config:
        populate_by_name = True


class DeviceInfo(BaseModel):
    """기기 정보"""

    device_model_code: str = Field(
        ..., alias="deviceModelCode", description="단말모델코드"
    )
    device_name: str = Field(..., alias="deviceName", description="단말모델명")
    device_pet_name: str = Field(..., alias="devicePetName", description="팻네임")

    class Config:
        populate_by_name = True


class RuleCheckResult(BaseModel):
    """규칙 체크 결과"""

    error_code: str = Field(..., alias="errorCode", description="에러코드")
    error_message: str = Field(..., alias="errorMessage", description="에러메시지")

    class Config:
        populate_by_name = True


class MobilePlanBenefitInfo(BaseModel):
    """모바일 플랜 혜택 정보"""

    curr_benefits: List[BenefitInfo] = Field(
        default=[], alias="currBenefits", description="현재혜택목록"
    )
    selective_option_num: str = Field(
        ..., alias="selectiveOptionNum", description="선택제공가능갯수"
    )
    next_benefits: List[BenefitInfo] = Field(
        default=[], alias="nextBenefits", description="다음혜택목록"
    )
    customer_benefits: List[CustomerBenefit] = Field(
        default=[], alias="customerBenefits", description="고객혜택목록"
    )

    class Config:
        populate_by_name = True


class InformationList(BaseModel):
    """정보 목록"""

    automatically_terminated_product_list: List[PMProductInfo] = Field(
        default=[],
        alias="automaticallyTerminatedProductList",
        description="자동해지상품목록",
    )
    automatically_enrolled_product_list: List[PMProductInfo] = Field(
        default=[],
        alias="automaticallyEnrolledProductList",
        description="자동가입상품목록",
    )
    pre_termination_required_product_list: List[PMProductInfo] = Field(
        default=[],
        alias="preTerminationRequiredProductList",
        description="사전해지필요상품목록",
    )
    non_assigned_product_list: List[PMProductInfo] = Field(
        default=[], alias="nonAssignedProductList", description="미배정상품목록"
    )
    pre_termination_required_campaign_list: List[PMCampaignInfo] = Field(
        default=[],
        alias="preTerminationRequiredCampaignList",
        description="사전해지필요캐페인목록",
    )
    mobile_plan_benefit_info: MobilePlanBenefitInfo = Field(
        ..., alias="mobilePlanBenefitInfo", description="모바일플랜혜택정보"
    )

    class Config:
        populate_by_name = True


class SubscriptionConditionSummary(BaseModel):
    """가입 조건 요약"""

    scrb_cond_src: str = Field(..., alias="scrbCondSrc", description="가입조건출처")
    scrb_psbl_yn: str = Field(..., alias="scrbPsblYn", description="가입가능여부")

    class Config:
        populate_by_name = True


class LegacyCondition(BaseModel):
    """레거시 조건"""

    scrb_psbl_yn: str = Field(..., alias="scrbPsblYn", description="가입가능여부")
    scrb_imposs_rsn: str = Field(..., alias="scrbImpossRsn", description="가입불가사유")
    scrb_prod_list: List[ProductInfo] = Field(
        default=[], alias="scrbProdList", description="가입상품목록"
    )
    term_prod_list: List[ProductInfo] = Field(
        default=[], alias="termProdList", description="해지상품목록"
    )

    class Config:
        populate_by_name = True


class PMCondition(BaseModel):
    """PM 조건"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    product_id: str = Field(..., alias="productID", description="상품ID")
    available: bool = Field(..., alias="available", description="가입가능여부")
    device: DeviceInfo = Field(..., alias="device", description="기기정보")
    rule_check_result: List[RuleCheckResult] = Field(
        default=[], alias="ruleCheckResult", description="규칙체크결과목록"
    )
    information_list: InformationList = Field(
        ..., alias="informationList", description="정보목록"
    )
    product_relation_error: ProductRelationError = Field(
        ..., alias="productRelationError", description="상품연관조건오류"
    )
    campaign_relation_error: CampaignRelationError = Field(
        ..., alias="CampaignRelationError", description="혜택연관조건오류"
    )

    class Config:
        populate_by_name = True


class PlanSubscriptionPreview(BaseModel):
    """요금제 가입 미리보기 정보"""

    leg_cond: LegacyCondition = Field(..., alias="legCond", description="레거시조건")
    pm_cond: PMCondition = Field(..., alias="pmCond", description="PM조건")
    scrb_cond_smry: SubscriptionConditionSummary = Field(
        ..., alias="scrbCondSmry", description="가입조건요약"
    )

    class Config:
        populate_by_name = True
