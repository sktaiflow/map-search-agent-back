from typing import List, Optional

from pydantic import BaseModel, Field


class ServiceInfo(BaseModel):
    """서비스 정보"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_num: str = Field(..., alias="svcNum", description="서비스번호")


class ChildInfo(BaseModel):
    """자녀 정보"""

    cust_num: str = Field(..., alias="custNum", description="자녀고객번호")
    svc_list: List[ServiceInfo] = Field(..., alias="svcList", description="서비스 목록")


class CustomerChildren(BaseModel):
    """법정대리인 자녀 정보"""

    chld_reg_yn: str = Field(..., alias="chldRegYn", description="자녀등록여부")
    chld_list: List[ChildInfo] = Field(default=[], alias="chldList", description="자녀 목록")

    class Config:
        populate_by_name = True


class MilitaryService(BaseModel):
    """군 입영 정보"""

    army_unit_dt: str = Field(..., alias="armyUnitDt", description="군입영일자")
    audit_dtm: str = Field(..., alias="auditDtm", description="최종변경일시")
    armysvc_typ_cd: str = Field(..., alias="armysvcTypCd", description="복무유형")
    army_mrd_dt: str = Field(..., alias="armyMrdDt", description="전역예정일자")

    class Config:
        populate_by_name = True


class MobileContractDevice(BaseModel):
    """무선 회선 기본 가입정보"""

    svc_scrb_dt: str = Field(..., alias="svcScrbDt", description="가입일자YYYYMMDD")
    dvc_dtl_yn: Optional[str] = Field(None, alias="dvcDtlYn", description="가입정보존재여부")
    eqp_mdl_cd: Optional[str] = Field(None, alias="eqpMdlCd", description="단말기모델코드")
    eqp_mdl_nm: Optional[str] = Field(None, alias="eqpMdlNm", description="단말기모델명")
    rmk: Optional[str] = Field(None, description="단말기팻네임")
    svc_st_cd: Optional[str] = Field(None, alias="svcStCd", description="서비스상태코드")
    svc_st_nm: Optional[str] = Field(None, alias="svcStNm", description="서비스상태명")
    usim_typ_cd: Optional[str] = Field(None, alias="usimTypCd", description="USIM유형코드")
    usim_typ_nm: Optional[str] = Field(None, alias="usimTypNm", description="USIM유형명")
    last_scrb_typ_nm: Optional[str] = Field(
        None, alias="lastScrbTypNm", description="최종가입유형명"
    )
    last_scrb_dt: Optional[str] = Field(
        None, alias="lastScrbDt", description="최종가입일자YYYYMMDD"
    )
    last_scrb_org_nm: Optional[str] = Field(
        None, alias="lastScrbOrgNm", description="최종처리조직명"
    )
    cust_num: Optional[str] = Field(None, alias="custNum", description="고객번호")
    cust_nm: Optional[str] = Field(None, alias="custNm", description="고객명")
    cust_typ_cd: Optional[str] = Field(None, alias="custTypCd", description="고객유형코드")
    cust_typ_nm: Optional[str] = Field(None, alias="custTypNm", description="고객유형명")
    cust_dtl_typ_cd: Optional[str] = Field(
        None, alias="custDtlTypCd", description="고객세부유형코드"
    )
    cust_dtl_typ_nm: Optional[str] = Field(None, alias="custDtlTypNm", description="고객세부유형명")
    svc_typ_cd: Optional[str] = Field(None, alias="svcTypCd", description="서비스유형코드")
    svc_typ_nm: Optional[str] = Field(None, alias="svcTypNm", description="서비스유형명")
    fee_prod_id: Optional[str] = Field(None, alias="feeProdId", description="요금상품ID")
    fee_prod_nm: Optional[str] = Field(None, alias="feeProdNm", description="요금상품명")
    susp_day_cnt: Optional[str] = Field(None, alias="suspDayCnt", description="정지일수")
    ltrm_dc_strd_dt: Optional[str] = Field(
        None, alias="ltrmDcStrdDt", description="장기할인기준일자"
    )
    new_ltrm_dc_dt: Optional[str] = Field(
        None, alias="newLtrmDcDt", description="신규장기할인기준일자"
    )
    scrb_yr_cnt: Optional[str] = Field(None, alias="scrbYrCnt", description="가입년수")
    scrb_yy_cnt: Optional[str] = Field(None, alias="scrbYyCnt", description="장기가입기간년")
    scrb_mm_cnt: Optional[str] = Field(None, alias="scrbMmCnt", description="장기가입기간월")
    scrb_dd_cnt: Optional[str] = Field(None, alias="scrbDdCnt", description="장기가입기간")
    rem_mth_cnt: Optional[str] = Field(None, alias="remMthCnt", description="잔여개월수")

    class Config:
        populate_by_name = True


class AllotmentDetail(BaseModel):
    """할부 상세 정보"""

    eqp_mdl_nm: str = Field(..., alias="eqpMdlNm", description="모델명")
    allot_sta_dt: str = Field(..., alias="allotStaDt", description="할부시작일자YYYYMMDD")
    allot_tot_mth_cnt: str = Field(..., alias="allotTotMthCnt", description="할부총개월")
    allot_rem_mth_cnt: str = Field(..., alias="allotRemMthCnt", description="할부잔여개월")
    allot_tot_amt: str = Field(..., alias="allotTotAmt", description="할부총금액")
    allot_rem_amt: str = Field(..., alias="allotRemAmt", description="할부잔여금액")

    class Config:
        populate_by_name = True


class ContractDetail(BaseModel):
    """약정 상세 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    sta_dt: str = Field(..., alias="staDt", description="시작일자YYYYMMDD")
    end_dt: str = Field(..., alias="endDt", description="종료일자YYYYMMDD")
    dc_amt: str = Field(..., alias="dcAmt", description="할인금액")
    pen_amt: str = Field(..., alias="penAmt", description="할인반환금금액")

    class Config:
        populate_by_name = True


class RemainContractDetail(BaseModel):
    """잔여 약정 상세 정보"""

    flx_cntrct_scrb_yn: str = Field(..., alias="flxCntrctScrbYn", description="선택약정가입여부")
    flx_cntrct_dtl: Optional[ContractDetail] = Field(
        None, alias="flxCntrctDtl", description="선택약정 상세"
    )
    plan_cntrct_scrb_yn: str = Field(..., alias="planCntrctScrbYn", description="요금약정가입여부")
    recnt_term_plan_cntrct_yn: str = Field(
        ..., alias="recntTermPlanCntrctYn", description="최근종료된요금약정유무"
    )
    plan_cntrct_dtl: Optional[ContractDetail] = Field(
        None, alias="planCntrctDtl", description="요금약정 상세"
    )
    tsuprt_cntrct_scrb_yn: str = Field(
        ..., alias="tsuprtCntrctScrbYn", description="T지원금약정가입여부"
    )
    recnt_term_tsuprt_cntrct_yn: str = Field(
        ..., alias="recntTermTsuprtCntrctYn", description="최근종료된T지원금약정유무"
    )
    tsuprt_cntrct_dtl: Optional[ContractDetail] = Field(
        None, alias="tsuprtCntrctDtl", description="T지원금약정 상세"
    )
    tsuprt_cntrct_trnsf_yn: str = Field(
        ..., alias="tsuprtCntrctTrnsfYn", description="T지원금약정승계여부"
    )
    tsuprt_cntrct_trnsf_dtl: Optional[ContractDetail] = Field(
        None, alias="tsuprtCntrctTrnsfDtl", description="T지원금약정승계 상세"
    )
    cntrct_pen2_yn: str = Field(..., alias="cntrctPen2Yn", description="약정위약금2여부")
    recnt_term_cntrct_pen2_yn: str = Field(
        ..., alias="recntTermCntrctPen2Yn", description="최근종료된약정위약금2유무"
    )
    cntrct_pen2_dtl: Optional[ContractDetail] = Field(
        None, alias="cntrctPen2Dtl", description="약정위약금2 상세"
    )
    cntrct_pen2_trnsf_yn: str = Field(
        ..., alias="cntrctPen2TrnsfYn", description="약정위약금2승계여부"
    )
    cntrct_pen2_trnsf_dtl: Optional[ContractDetail] = Field(
        None, alias="cntrctPen2TrnsfDtl", description="약정위약금2승계 상세"
    )
    etc_cntrt_scrb_yn: str = Field(..., alias="etcCntrtScrbYn", description="기타약정가입여부")
    recnt_term_trental_yn: str = Field(
        ..., alias="recntTermTrentalYn", description="최근종료된T렌탈유무"
    )

    class Config:
        populate_by_name = True


class ContractRemainInfo(BaseModel):
    """계약 잔여 정보"""

    rem_allot_yn: str = Field(..., alias="remAllotYn", description="잔여할부유무")
    rem_allot_dtl: Optional[AllotmentDetail] = Field(
        None, alias="remAllotDtl", description="잔여할부 상세"
    )
    recnt_term_allot_yn: str = Field(
        ..., alias="recntTermAllotYn", description="최근종료된할부유무"
    )
    rem_cntrct_yn: str = Field(..., alias="remCntrctYn", description="잔여약정유무")
    rem_cntrct_dtl: Optional[RemainContractDetail] = Field(
        None, alias="remCntrctDtl", description="잔여약정 상세"
    )
    usable_no_cntrct_pt_yn: str = Field(
        ..., alias="usableNoCntrctPtYn", description="사용가능무약정포인트유무"
    )

    class Config:
        populate_by_name = True


class NoContractPoint(BaseModel):
    """무약정 포인트 정보"""

    tot_accum_pt: str = Field(..., alias="totAccumPt", description="총적립포인트")
    tot_used_pt: str = Field(..., alias="totUsedPt", description="총사용포인트")
    tot_expir_pt: str = Field(..., alias="totExpirPt", description="총소멸포인트")
    tot_rem_pt: str = Field(..., alias="totRemPt", description="총잔여포인트")
    nxt_schd_expir_dt: str = Field(
        ..., alias="nxtSchdExpirDt", description="다음만료예정일YYYYMMDD"
    )
    nxt_schd_expir_pt: str = Field(..., alias="nxtSchdExpirPt", description="다음만료예정포인트")
    scrb_days: str = Field(..., alias="scrbDays", description="가입경과일")
    use_psbl_dt: str = Field(..., alias="usePsblDt", description="사용가능일자YYYYMMDD")

    class Config:
        populate_by_name = True


class DirectPlanDetail(BaseModel):
    """다이렉트플랜 상세 정보"""

    org_id: str = Field(..., alias="orgId", description="구매영업장ID")
    org_nm: str = Field(..., alias="orgNm", description="구매영업장명")
    org_abbr_nm: str = Field(..., alias="orgAbbrNm", description="구매영업장약어명")
    org_cd: str = Field(..., alias="orgCd", description="조직코드")
    sub_org_cd: str = Field(..., alias="subOrgCd", description="서브조직코드")
    svc_chg_cd: str = Field(..., alias="svcChgCd", description="서비스변경코드-이동전화가입유형")
    svc_chg_rsn_cd: str = Field(..., alias="svcChgRsnCd", description="서비스변경사유코드")
    chg_dtm: str = Field(..., alias="chgDtm", description="변경일시")
    scrb_psbl_org_cd_yn: str = Field(..., alias="scrbPsblOrgCdYn", description="가입가능조직여부")

    class Config:
        populate_by_name = True


class DeviceContract(BaseModel):
    """기기 계약 정보"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_num: str = Field(..., alias="svcNum", description="서비스번호")
    eqp_chg_dt: str = Field(..., alias="eqpChgDt", description="가입기변최종변경(처리)일자YYYYMMDD")
    eqp_rel_chg_cd: str = Field(..., alias="eqpRelChgCd", description="가입기변최종변경코드")
    tsuprt_cntrct_scrb_yn: str = Field(
        ..., alias="tsuprtCntrctScrbYn", description="T지원금약정사용여부"
    )
    tsuprt_cntrct_trnsf_psbl_yn: str = Field(
        ..., alias="tsuprtCntrctTrnsfPsblYn", description="T지원금약정승계가능여부"
    )
    tsuprt_cntrct_passovr_day_cnt: str = Field(
        ...,
        alias="tsuprtCntrctPassovrDayCnt",
        description="T지원금약정일반일기준경과일수",
    )
    tsuprt_cntrct_passovr_wday_cnt: str = Field(
        ...,
        alias="tsuprtCntrctPassovrWdayCnt",
        description="T지원금약정영업일기준경과일수",
    )
    flx_cntrct_scrb_psbl_yn: str = Field(
        ..., alias="flxCntrctScrbPsblYn", description="선택약정가입가능여부"
    )
    flx_cntrct_trnsf_psbl_yn: str = Field(
        ..., alias="flxCntrctTrnsfPsblYn", description="선택약정승계가능여부"
    )
    flx_cntrct_passovr_day_cnt: str = Field(
        ..., alias="flxCntrctPassovrDayCnt", description="선택약정일반일기준경과일수"
    )
    flx_cntrct_passovr_wday_cnt: str = Field(
        ..., alias="flxCntrctPassovrWdayCnt", description="선택약정영업일기준경과일수"
    )
    direct_plan_dtl_list: List[DirectPlanDetail] = Field(
        ..., alias="directPlanDtlList", description="다이렉트플랜 상세 목록"
    )

    class Config:
        populate_by_name = True


class MobileService(BaseModel):
    """모바일 서비스 정보"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_num: str = Field(..., alias="svcNum", description="서비스번호")
    svc_cd: str = Field(..., alias="svcCd", description="서비스구분코드")
    svc_st_cd: str = Field(..., alias="svcStCd", description="서비스상태코드")
    svc_st_chg_cd: str = Field(..., alias="svcStChgCd", description="서비스상태변경코드")
    svc_chg_rsn_cd: str = Field(..., alias="svcChgRsnCd", description="서비스변경사유코드")
    svc_typ_cd: str = Field(..., alias="svcTypCd", description="서비스이용종류코드")
    svc_scrb_dtm: str = Field(..., alias="svcScrbDtm", description="서비스가입일자")
    scrb_req_rsn_cd: str = Field(..., alias="scrbReqRsnCd", description="가입신청사유코드")
    wlf_dc_cd: str = Field(..., alias="wlfDcCd", description="복지할인유형코드")
    estation_agree_yn: str = Field(..., alias="estationAgreeYn", description="웹회원신청동의여부")
    fee_prod_id: str = Field(..., alias="feeProdId", description="요금상품ID")
    fee_prod_nm: str = Field(..., alias="feeProdNm", description="요금상품명")
    fee_prod_chg_dt: str = Field(..., alias="feeProdChgDt", description="요금제변경일자")
    eqp_mdl_cd: str = Field(..., alias="eqpMdlCd", description="단말기모델코드")
    eqp_mdl_nm: str = Field(..., alias="eqpMdlNm", description="단말기모델명")
    eqp_ser_num: str = Field(..., alias="eqpSerNum", description="단말기일련번호")
    eqp_usg_cd: str = Field(..., alias="eqpUsgCd", description="단말기용도코드")
    eqp_mthd_cd: str = Field(..., alias="eqpMthdCd", description="단말기방식코드")
    eqp_mktg_dt: str = Field(..., alias="eqpMktgDt", description="단말기출시일자")
    nw_mthd_cd: str = Field(..., alias="nwMthdCd", description="네트워크방식코드")
    cust_num: str = Field(..., alias="custNum", description="고객번호")

    class Config:
        populate_by_name = True


class RemainingAllotmentDetail(BaseModel):
    """잔여 할부 상세 정보"""

    eqp_mdl_nm: str = Field(..., alias="eqpMdlNm", description="모델명")
    allot_sta_dt: str = Field(..., alias="allotStaDt", description="할부시작일자YYYYMMDD")
    allot_tot_mth_cnt: str = Field(..., alias="allotTotMthCnt", description="할부총개월")
    allot_rem_mth_cnt: str = Field(..., alias="allotRemMthCnt", description="할부잔여개월")
    allot_tot_amt: str = Field(..., alias="allotTotAmt", description="할부총금액")
    allot_rem_amt: str = Field(..., alias="allotRemAmt", description="할부잔여금액")

    class Config:
        populate_by_name = True


class FlexibleContractDetail(BaseModel):
    """선택약정 상세 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    sta_dt: str = Field(..., alias="staDt", description="시작일자YYYYMMDD")
    end_dt: str = Field(..., alias="endDt", description="종료일자YYYYMMDD")
    dc_amt: str = Field(..., alias="dcAmt", description="할인금액")
    pen_amt: str = Field(..., alias="penAmt", description="할인반환금금액")

    class Config:
        populate_by_name = True


class PlanContractDetail(BaseModel):
    """요금약정 상세 정보"""

    prod_id: str = Field(..., alias="prodId", description="상품ID")
    sta_dt: str = Field(..., alias="staDt", description="시작일자YYYYMMDD")
    end_dt: str = Field(..., alias="endDt", description="종료일자YYYYMMDD")
    dc_amt: str = Field(..., alias="dcAmt", description="할인금액")
    pen_amt: str = Field(..., alias="penAmt", description="할인반환금금액")

    class Config:
        populate_by_name = True


class TSupportContractDetail(BaseModel):
    """T지원금약정 상세 정보"""

    sta_dt: str = Field(..., alias="staDt", description="시작일자YYYYMMDD")
    end_dt: str = Field(..., alias="endDt", description="종료일자YYYYMMDD")
    dc_amt: str = Field(..., alias="dcAmt", description="할인금액")
    pen_amt: str = Field(..., alias="penAmt", description="할인반환금금액")

    class Config:
        populate_by_name = True


class ContractPenalty2Detail(BaseModel):
    """약정위약금2 상세 정보"""

    sta_dt: str = Field(..., alias="staDt", description="시작일자YYYYMMDD")
    end_dt: str = Field(..., alias="endDt", description="종료일자YYYYMMDD")
    dc_amt: str = Field(..., alias="dcAmt", description="할인금액")
    pen_amt: str = Field(..., alias="penAmt", description="할인반환금금액")

    class Config:
        populate_by_name = True


class RemainingContractDetail(BaseModel):
    """잔여 약정 상세 정보"""

    flx_cntrct_scrb_yn: str = Field(..., alias="flxCntrctScrbYn", description="선택약정가입여부")
    flx_cntrct_dtl: Optional[FlexibleContractDetail] = Field(
        None, alias="flxCntrctDtl", description="선택약정상세"
    )
    plan_cntrct_scrb_yn: str = Field(..., alias="planCntrctScrbYn", description="요금약정가입여부")
    recnt_term_plan_cntrct_yn: str = Field(
        ..., alias="recntTermPlanCntrctYn", description="최근종료된요금약정유무"
    )
    plan_cntrct_dtl: Optional[PlanContractDetail] = Field(
        None, alias="planCntrctDtl", description="요금약정상세"
    )
    tsuprt_cntrct_scrb_yn: str = Field(
        ..., alias="tsuprtCntrctScrbYn", description="T지원금약정가입여부"
    )
    recnt_term_tsuprt_cntrct_yn: str = Field(
        ..., alias="recntTermTsuprtCntrctYn", description="최근종료된T지원금약정유무"
    )
    tsuprt_cntrct_dtl: Optional[TSupportContractDetail] = Field(
        None, alias="tsuprtCntrctDtl", description="T지원금약정상세"
    )
    tsuprt_cntrct_trnsf_yn: str = Field(
        ..., alias="tsuprtCntrctTrnsfYn", description="T지원금약정승계여부"
    )
    tsuprt_cntrct_trnsf_dtl: Optional[TSupportContractDetail] = Field(
        None, alias="tsuprtCntrctTrnsfDtl", description="T지원금약정승계상세"
    )
    cntrct_pen2_yn: str = Field(..., alias="cntrctPen2Yn", description="약정위약금2여부")
    recnt_term_cntrct_pen2_yn: str = Field(
        ..., alias="recntTermCntrctPen2Yn", description="최근종료된약정위약금2유무"
    )
    cntrct_pen2_dtl: Optional[ContractPenalty2Detail] = Field(
        None, alias="cntrctPen2Dtl", description="약정위약금2상세"
    )
    cntrct_pen2_trnsf_yn: str = Field(
        ..., alias="cntrctPen2TrnsfYn", description="약정위약금2승계여부"
    )
    cntrct_pen2_trnsf_dtl: Optional[ContractPenalty2Detail] = Field(
        None, alias="cntrctPen2TrnsfDtl", description="약정위약금2승계상세"
    )
    etc_cntrt_scrb_yn: str = Field(..., alias="etcCntrtScrbYn", description="기타약정가입여부")
    recnt_term_trental_yn: str = Field(
        ..., alias="recntTermTrentalYn", description="최근종료된T렌탈유무"
    )

    class Config:
        populate_by_name = True


class RemainedContract(BaseModel):
    """잔여 약정 정보"""

    rem_allot_yn: str = Field(..., alias="remAllotYn", description="잔여할부유무")
    rem_allot_dtl: Optional[RemainingAllotmentDetail] = Field(
        None, alias="remAllotDtl", description="잔여할부상세"
    )
    recnt_term_allot_yn: str = Field(
        ..., alias="recntTermAllotYn", description="최근종료된할부유무"
    )
    rem_cntrct_yn: str = Field(..., alias="remCntrctYn", description="잔여약정유무")
    rem_cntrct_dtl: Optional[RemainingContractDetail] = Field(
        None, alias="remCntrctDtl", description="잔여약정상세"
    )
    usable_no_cntrct_pt_yn: str = Field(
        ..., alias="usableNoCntrctPtYn", description="사용가능무약정포인트유무"
    )

    class Config:
        populate_by_name = True


class DeviceInfo(BaseModel):
    """기기 정보"""

    eqp_mdl_cd: str = Field(..., alias="eqpMdlCd", description="단말기모델코드")
    eqp_mdl_nm: str = Field(..., alias="eqpMdlNm", description="단말기모델명")
    eqp_rmk: Optional[str] = Field(None, alias="eqpRmk", description="단말기펫네임")
    eqp_mthd_cd: str = Field(..., alias="eqpMthdCd", description="단말기방식코드")
    eqp_mktg_dt: str = Field(..., alias="eqpMktgDt", description="단말기출시일자")

    class Config:
        populate_by_name = True
