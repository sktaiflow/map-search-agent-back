from typing import List, Optional

from pydantic import BaseModel, Field


class AddOnProduct(BaseModel):
    """부가서비스 상품 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    prod_nm: str = Field(..., alias="prodNm", description="상품명")
    fix_amt_amt: str = Field(..., alias="fixAmtAmt", description="정액료금액")

    class Config:
        populate_by_name = True


class SupplementaryPlan(BaseModel):
    """보조요금제 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    prod_nm: str = Field(..., alias="prodNm", description="상품명")
    bas_fee_amt: str = Field(..., alias="basFeeAmt", description="기본료금액")

    class Config:
        populate_by_name = True


class AddOnSubscriptions(BaseModel):
    """부가서비스 가입정보"""

    add_on_cnt: str = Field(..., alias="addOnCnt", description="가입중부가서비스갯수")
    free_add_on_cnt: str = Field(..., alias="freeAddOnCnt", description="가입중무료부가서비스갯수")
    paid_add_on_cnt: str = Field(..., alias="paidAddOnCnt", description="가입중유료부가서비스갯수")
    free_add_on_list: List[AddOnProduct] = Field(
        default=[], alias="freeAddOnList", description="무료부가서비스목록"
    )
    paid_add_on_list: List[AddOnProduct] = Field(
        default=[], alias="paidAddOnList", description="유료부가서비스목록"
    )
    supl_plan_list: List[SupplementaryPlan] = Field(
        default=[], alias="suplPlanList", description="보조요금제목록"
    )
    smart_call_pick_list: List[AddOnProduct] = Field(
        default=[], alias="smartCallPickList", description="스마트콜픽목록"
    )

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
    free_add_on_cnt: str = Field(..., alias="freeAddOnCnt", description="가입중무료부가서비스갯수")
    paid_add_on_cnt: str = Field(..., alias="paidAddOnCnt", description="가입중유료부가서비스갯수")
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
    legacy_product_id: str = Field(..., alias="legacyProductId", description="Legacy상품ID")
    product_name: str = Field(..., alias="productName", description="상품명")

    class Config:
        populate_by_name = True


class PMCampaignInfo(BaseModel):
    """PM 캠페인 정보"""

    pm_campaign_id: str = Field(..., alias="pmCampaignId", description="PM혜택ID")
    campaign_name: str = Field(..., alias="campaignName", description="혜택명")

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

    class Config:
        populate_by_name = True


class AddOnHistory(BaseModel):
    """부가서비스 이력 정보"""

    pass  # docstring에서 구체적인 필드 정보를 찾지 못했습니다


class BasicPlanCondition(BaseModel):
    """기본요금제 조건 정보"""

    recnt_plan_chg_yn: str = Field(..., alias="recntPlanChgYn", description="최근요금제변경여부")
    plan_last_chg_dt: str = Field(..., alias="planLastChgDt", description="요금제최종변경일자")
    plan_chg_psbl_dt: str = Field(..., alias="planChgPsblDt", description="요금제변경가능일자")
    plan_chg_cnt_tday: str = Field(..., alias="planChgCntTday", description="당일요금변경건수")
    plan_chg_psbl_tday_yn: str = Field(
        ..., alias="planChgPsblTdayYn", description="당일요금변경가능여부"
    )
    plan_chg_cnt_tmth: str = Field(..., alias="planChgCntTmth", description="당월요금변경건수")
    plan_chg_psbl_tmth_yn: str = Field(
        ..., alias="planChgPsblTmthYn", description="당월요금변경가능여부"
    )

    class Config:
        populate_by_name = True


class FlexibleContractRenewal(BaseModel):
    """유연약정 자동갱신 정보"""

    auto_rnwl_scrb_yn: str = Field(..., alias="autoRnwlScrbYn", description="사전신청가입여부")
    auto_rnwl_scrb_psbl_dt: str = Field(
        ..., alias="autoRnwlScrbPsblDt", description="사전신청가입가능일자"
    )
    expir_cond_trgt_yn: str = Field(
        ..., alias="expirCondTrgtYn", description="약정만기조건대상자여부"
    )
    expir_rem_day_cnt: str = Field(..., alias="expirRemDayCnt", description="약정만기잔여일수")
    expir_dt: str = Field(..., alias="expirDt", description="약정만기일자")
    new_cond_trgt_yn: str = Field(..., alias="newCondTrgtYn", description="신규조건대상자여부")

    class Config:
        populate_by_name = True


class DeviceInfo(BaseModel):
    """기기 정보"""

    device_model_code: str = Field(..., alias="deviceModelCode", description="단말모델코드")
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
        description="사전해지필요캠페인목록",
    )
    mobile_plan_benefit_info: MobilePlanBenefitInfo = Field(
        ..., alias="mobilePlanBenefitInfo", description="모바일플랜혜택정보"
    )

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
    information_list: InformationList = Field(..., alias="informationList", description="정보목록")

    class Config:
        populate_by_name = True


class PlanSubscriptionPreview(BaseModel):
    """요금제 가입 미리보기 정보"""

    leg_cond: LegacyCondition = Field(..., alias="legCond", description="레거시조건")
    pm_cond: PMCondition = Field(..., alias="pmCond", description="PM조건")

    class Config:
        populate_by_name = True


class CombinationGroupMember(BaseModel):
    """결합할인 그룹 멤버"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_num: str = Field(..., alias="svcNum", description="서비스번호")
    cust_num: str = Field(..., alias="custNum", description="고객번호")
    cust_nm: str = Field(..., alias="custNm", description="고객명")
    wless_scrb_yr_cnt: str = Field(..., alias="wlessScrbYrCnt", description="이동전화가입년수")

    class Config:
        populate_by_name = True


class CombinationGroupPreview(BaseModel):
    """결합할인 그룹 미리보기 정보"""

    grp_tot_scrb_yr_cnt: str = Field(..., alias="grpTotScrbYrCnt", description="그룹합산년수")
    grp_expt_yr_dc_amt: str = Field(
        ..., alias="grpExptYrDcAmt", description="그룹연간기본료할인예상금액"
    )
    grp_expt_mth_dc_amt: str = Field(
        ..., alias="grpExptMthDcAmt", description="그룹월기본료할인예상금액"
    )
    scrb_psbl_yn: str = Field(..., alias="scrbPsblYn", description="가입가능여부")
    scrb_imposs_rsn: str = Field(..., alias="scrbImpossRsn", description="가입불가사유")
    grp_list: List[CombinationGroupMember] = Field(
        default=[], alias="grpList", description="그룹목록"
    )

    class Config:
        populate_by_name = True


class WirelessMember(BaseModel):
    """무선 멤버 정보"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    rel_cl_cd: str = Field(..., alias="relClCd", description="서비스구분")
    fee_prod_id: str = Field(..., alias="feeProdId", description="기본요금제ID")
    fee_prod_nm: str = Field(..., alias="feeProdNm", description="기본요금제명")
    scrb_yr_cnt: str = Field(..., alias="scrbYrCnt", description="가입년수")
    tc_fee_benf: str = Field(..., alias="tcFeeBenf", description="할인정보")
    data_benf: str = Field(..., alias="dataBenf", description="추가정보")
    bas_fee_dc: str = Field(..., alias="basFeeDc", description="할인금액(세금제외)")
    bas_fee_dc_tx: str = Field(..., alias="basFeeDcTx", description="할인금액(세금제외)")
    bas_fee_amt: str = Field(..., alias="basFeeAmt", description="할인금액(세금제외)")
    bas_fee_amt_tx: str = Field(..., alias="basFeeAmtTx", description="월정액(세금포함)")
    comb_sta_dt: str = Field(..., alias="combStaDt", description="결합시작일")

    class Config:
        populate_by_name = True


class WiredMember(BaseModel):
    """유선 멤버 정보"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_cd: str = Field(..., alias="svcCd", description="서비스구분코드")
    svc_dtl_cl_cd: str = Field(..., alias="svcDtlClCd", description="서비스상세구분코드")
    fee_prod_id: str = Field(..., alias="feeProdId", description="기본요금제ID")
    fee_prod_nm: str = Field(..., alias="feeProdNm", description="기본요금제명")
    svc_tech_mthd_cd: str = Field(..., alias="svcTechMthdCd", description="서비스기술방식")
    giga_int_yn: str = Field(..., alias="gigaIntYn", description="기가인터넷여부")
    speed_cd: str = Field(..., alias="speedCd", description="속도정보")
    agrmt_dc_mth_cd: str = Field(..., alias="agrmtDcMthCd", description="약정기간")
    scrb_yr_cnt: str = Field(..., alias="scrbYrCnt", description="가입년수")
    tc_fee_benf: str = Field(..., alias="tcFeeBenf", description="할인정보")
    bas_fee_dc: str = Field(..., alias="basFeeDc", description="할인금액(세금제외)")
    bas_fee_dc_tx: str = Field(..., alias="basFeeDcTx", description="할인금액(세금제외)")
    bas_fee_amt: str = Field(..., alias="basFeeAmt", description="할인금액(세금제외)")
    bas_fee_amt_tx: str = Field(..., alias="basFeeAmtTx", description="월정액(세금포함)")
    regu_agrmt_dc: str = Field(..., alias="reguAgrmtDc", description="정기계약할인")
    comb_sta_dt: str = Field(..., alias="combStaDt", description="결합시작일")

    class Config:
        populate_by_name = True


class ServiceProductGroup(BaseModel):
    """서비스 상품 그룹 정보"""

    svc_prod_grp_cd: str = Field(..., alias="svcProdGrpCd", description="서비스상품그룹코드")
    svc_prod_grp_id: str = Field(..., alias="svcProdGrpId", description="서비스상품그룹ID")
    svc_prod_grp_nm: str = Field(..., alias="svcProdGrpNm", description="서비스상품그룹명")
    prod_id: str = Field(..., alias="prodId", description="상품ID")
    wless_mbr_list: List[WirelessMember] = Field(
        default=[], alias="wlessMbrList", description="무선멤버목록"
    )
    wire_mbr_list: List[WiredMember] = Field(
        default=[], alias="wireMbrList", description="유선멤버목록"
    )

    class Config:
        populate_by_name = True


class GroupMember(BaseModel):
    """그룹 멤버 정보"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_cd: str = Field(..., alias="svcCd", description="서비스구분")
    fee_prod_id: str = Field(..., alias="feeProdId", description="기본요금제ID")
    rep_svc_yn: str = Field(..., alias="repSvcYn", description="대표서비스여부")
    svc_prod_grp_attr_cd: str = Field(
        ..., alias="svcProdGrpAttrCd", description="서비스상품그룹속성코드"
    )

    class Config:
        populate_by_name = True


class CombinationGroup(BaseModel):
    """결합할인 그룹 정보"""

    svc_prod_grp_list: List[ServiceProductGroup] = Field(
        default=[], alias="svcProdGrpList", description="서비스상품그룹목록"
    )

    op_cl_cd: Optional[str] = Field(None, alias="opClCd", description="업무구분코드")
    svc_prod_grp_cd: Optional[str] = Field(
        None, alias="svcProdGrpCd", description="서비스상품그룹코드"
    )
    svc_prod_grp_id: Optional[str] = Field(
        None, alias="svcProdGrpId", description="서비스상품그룹ID"
    )
    grp_mbr_list: List[GroupMember] = Field(
        default=[], alias="grpMbrList", description="그룹멤버목록"
    )

    class Config:
        populate_by_name = True
