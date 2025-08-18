from typing import List

from pydantic import BaseModel, Field


class AccountPeriodAmount(BaseModel):
    """계정 납기월 미납금액 정보"""

    acnt_prd_pay_ym: str = Field(..., alias="acntPrdPayYm", description="계정납기년월")
    acnt_prd_col_amt: str = Field(..., alias="acntPrdColAmt", description="계정납기월미납금액")

    class Config:
        populate_by_name = True


class ServicePeriodAmount(BaseModel):
    """서비스 납기월 미납금액 정보"""

    svc_prd_pay_ym: str = Field(..., alias="svcPrdPayYm", description="서비스납기년월")
    svc_prd_col_amt: str = Field(..., alias="svcPrdColAmt", description="서비스납기월미납금액")

    class Config:
        populate_by_name = True


class UnpaidBill(BaseModel):
    """미납 요금 정보"""

    acnt_rep_svc_yn: str = Field(..., alias="acntRepSvcYn", description="계정대표서비스여부")
    acnt_col_yn: str = Field(..., alias="acntColYn", description="계정미납유무")
    anct_col_mth_cnt: str = Field(..., alias="anctColMthCnt", description="계정미납개월수")
    acnt_col_amt: str = Field(..., alias="acntColAmt", description="계정미납요금")
    acnt_col_amt_list: List[AccountPeriodAmount] = Field(
        default=[], alias="acntColAmtList", description="계정미납금액목록"
    )
    pay_psbl_yn: str = Field(..., alias="payPsblYn", description="납부가능여부")
    max_ptp_dt: str = Field(..., alias="maxPtpDt", description="납부약속최대일자")
    svc_col_yn: str = Field(..., alias="svcColYn", description="서비스미납여부")
    svc_col_amt: str = Field(..., alias="svcColAmt", description="서비스미납금액")
    svc_tmth_col_amt: str = Field(..., alias="svcTmthColAmt", description="서비스당월청구금액")
    svc_tot_col_amt: str = Field(..., alias="svcTotColAmt", description="서비스합산금액")
    svc_col_mth_cnt: str = Field(..., alias="svcColMthCnt", description="서비스미납개월수")
    susp_sta_dt: str = Field(..., alias="suspStaDt", description="이용정지예정일자")
    col_susp_schd_yn: str = Field(..., alias="colSuspSchdYn", description="미납정지예정일대상여부")
    svc_st_cd: str = Field(..., alias="svcStCd", description="서비스상태코드")
    svc_st_chg_cd: str = Field(..., alias="svcStChgCd", description="서비스상태변경코드")
    svc_chg_rsn_cd: str = Field(..., alias="svcChgRsnCd", description="서비스변경사유코드")
    svc_col_amt_list: List[ServicePeriodAmount] = Field(
        default=[], alias="svcColAmtList", description="서비스미납금액목록"
    )
    acnt_chg_yn: str = Field(..., alias="acntChgYn", description="계정변경여부")
    use_obj_yn: str = Field(..., alias="useObjYn", description="정지해제대상여부")

    class Config:
        populate_by_name = True


class CurrentBillItem(BaseModel):
    """현재 요금 항목"""

    bill_itm_lcl_nm: str = Field(..., alias="billItmLclNm", description="청구항목대분류명")
    bill_itm_scl_nm: str = Field(..., alias="billItmSclNm", description="청구항목소분류명")
    bill_itm_nm: str = Field(..., alias="billItmNm", description="청구항목명")
    bill_amt: str = Field(..., alias="billAmt", description="청구금액")

    class Config:
        populate_by_name = True


class CurrentBill(BaseModel):
    """현재 요금 정보"""

    pps_yn: str = Field(..., alias="ppsYn", description="선불요금제여부")
    acnt_rep_svc_yn: str = Field(..., alias="acntRepSvcYn", description="청구대표서비스여부")
    this_mth_scrb_yn: str = Field(..., alias="thisMthScrbYn", description="당월가입여부")
    auto_pay_yn: str = Field(..., alias="autoPayYn", description="자동납부여부")
    auto_pay_mth_nm: str = Field(..., alias="autoPayMthNm", description="자동납부수단이름")
    card_auto_pay_yn: str = Field(..., alias="cardAutoPayYn", description="카드자동납부여부")
    card_eff_ym_st: str = Field(..., alias="cardEffYmSt", description="카드유효년월상태")
    card_eff_ym: str = Field(..., alias="cardEffYm", description="카드유효년월")
    drw_scht_dt: str = Field(..., alias="drwSchtDt", description="인출예정일자")
    unpaid_yn: str = Field(..., alias="unpaidYn", description="미납여부")
    acnt_chg_yn: str = Field(..., alias="acntChgYn", description="계정변경여부")
    chld_reg_yn: str = Field(..., alias="chldRegYn", description="자녀회선보유여부")
    curr_bill_amt: str = Field(..., alias="currBillAmt", description="실시간요금")
    from_dt: str = Field(..., alias="fromDt", description="시작일자")
    to_dt: str = Field(..., alias="toDt", description="종료일자")
    inv_bill_amt: str = Field(..., alias="invBillAmt", description="청구요금")
    inv_bill_amt_yn: str = Field(..., alias="invBillAmtYn", description="당월청구요금여부")
    pre_inv_bill_amt_yn: str = Field(..., alias="preInvBillAmtYn", description="전월청구요금여부")
    integ_inv_yn: str = Field(..., alias="integInvYn", description="통합청구여부")
    curr_bill_list: List[CurrentBillItem] = Field(
        default=[], alias="currBillList", description="실시간요금목록"
    )

    class Config:
        populate_by_name = True


class CurrentBillChildItem(BaseModel):
    """자녀 현재 요금 항목"""

    svc_num: str = Field(..., alias="svcNum", description="서비스번호")
    curr_bill_amt: str = Field(..., alias="currBillAmt", description="실시간요금")
    inv_bill_amt: str = Field(..., alias="invBillAmt", description="청구요금")

    class Config:
        populate_by_name = True


class CurrentBillChildren(BaseModel):
    """자녀 현재 요금 정보"""

    chld_list: List[CurrentBillChildItem] = Field(
        default=[], alias="chldList", description="자녀요금목록"
    )

    class Config:
        populate_by_name = True


class FixedBillService(BaseModel):
    """정액 요금 서비스 정보"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_num: str = Field(..., alias="svcNum", description="서비스번호")
    svc_nm: str = Field(..., alias="svcNm", description="서비스명")
    svc_cd: str = Field(..., alias="svcCd", description="서비스코드")

    class Config:
        populate_by_name = True


class FixedBillItem(BaseModel):
    """정액 요금 항목"""

    itm_lcl_nm: str = Field(..., alias="itmLclNm", description="대분류명")
    itm_mcl_nm: str = Field(..., alias="itmMclNm", description="중분류명")
    itm_nm: str = Field(..., alias="itmNm", description="청구항목명")
    itm_bill_amt: str = Field(..., alias="itmBillAmt", description="청구금액")
    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")

    class Config:
        populate_by_name = True


class FixedBill(BaseModel):
    """정액 요금 정보"""

    pps_yn: str = Field(..., alias="ppsYn", description="선불요금제여부")
    inv_sta_dt: str = Field(..., alias="invStaDt", description="청구시작일자")
    inv_dt: str = Field(..., alias="invDt", description="청구일자")
    inv_bill_amt: str = Field(..., alias="invBillAmt", description="총청구금액")
    acnt_chg_yn: str = Field(..., alias="acntChgYn", description="계정변경여부")
    svc_list: List[FixedBillService] = Field(default=[], alias="svcList", description="서비스목록")
    itm_list: List[FixedBillItem] = Field(default=[], alias="itmList", description="청구항목목록")

    class Config:
        populate_by_name = True


class MobilePaymentItem(BaseModel):
    """모바일 결제 항목"""

    pg_nm: str = Field(..., alias="pgNm", description="서비스업체")
    bill_amt: str = Field(..., alias="billAmt", description="결제금액")

    class Config:
        populate_by_name = True


class MobilePayment(BaseModel):
    """모바일 결제 정보"""

    adult_yn: str = Field(..., alias="adultYn", description="성인여부")
    brws_psbl_yn: str = Field(..., alias="brwsPsblYn", description="조회가능여부")
    inv_bill_amt: str = Field(..., alias="invBillAmt", description="총청구금액")
    itm_list: List[MobilePaymentItem] = Field(
        default=[], alias="itmList", description="결제내역목록"
    )

    class Config:
        populate_by_name = True


class ContentPurchaseItem(BaseModel):
    """콘텐츠 구매 항목"""

    rgst_dtm: str = Field(..., alias="rgstDtm", description="결제일시")
    cp_nm: str = Field(..., alias="cpNm", description="서비스업체")
    cp_cntc: str = Field(..., alias="cpCntc", description="서비스업체문의처")
    ctt_nm: str = Field(..., alias="cttNm", description="컨텐츠명")
    ctt_typ_nm: str = Field(..., alias="cttTypNm", description="컨텐츠유형명")
    bill_amt: str = Field(..., alias="billAmt", description="결제금액")

    class Config:
        populate_by_name = True


class ContentPurchase(BaseModel):
    """콘텐츠 구매 정보"""

    brws_psbl_yn: str = Field(..., alias="brwsPsblYn", description="조회가능여부")
    inv_bill_amt: str = Field(..., alias="invBillAmt", description="총청구금액")
    itm_list: List[ContentPurchaseItem] = Field(
        default=[], alias="itmList", description="구매내역목록"
    )

    class Config:
        populate_by_name = True
