from typing import List

from pydantic import BaseModel, Field


class DataGiftSender(BaseModel):
    """데이터 선물 발신자 정보"""

    data_gift_psbl_yn: str = Field(..., alias="dataGiftPsblYn", description="선물하기가능여부")
    data_gift_st_cd: str = Field(..., alias="dataGiftStCd", description="선물하기상태코드")
    data_gift_st_msg: str = Field(..., alias="dataGiftStMsg", description="선물하기상태메세지")
    pen_aply_st_cd: str = Field(..., alias="penAplyStCd", description="선물제한상태코드")
    pen_aply_sta_dt: str = Field(..., alias="penAplyStaDt", description="선물제한시작일자")
    pen_aply_end_dt: str = Field(..., alias="penAplyEndDt", description="선물제한종료일자")
    plan_chg_cnt_tmth: str = Field(..., alias="planChgCntTmth", description="당월요금변경건수")
    adult_yn: str = Field(..., alias="adultYn", description="성인여부")
    fmly_yn: str = Field(..., alias="fmlyYn", description="가족결합여부")
    good_fmly_yn: str = Field(..., alias="goodFmlyYn", description="T가족결합여부")
    good_fmly_teen_shr_yn: str = Field(
        ..., alias="goodFmlyTeenShrYn", description="T가족결합_청소년공유여부"
    )
    gift_psbl_cnt: str = Field(..., alias="giftPsblCnt", description="일반선물가능횟수")
    fmly_gift_psbl_cnt: str = Field(..., alias="fmlyGiftPsblCnt", description="가족선물가능횟수")
    blklst_st_cd: str = Field(..., alias="blklstStCd", description="블랙리스트상태코드")

    class Config:
        populate_by_name = True


class DataGiftLimit(BaseModel):
    """데이터 선물 한도 정보"""

    data_gift_psbl_yn: str = Field(..., alias="dataGiftPsblYn", description="선물하기가능여부")
    data_gift_st_cd: str = Field(..., alias="dataGiftStCd", description="선물하기상태코드")
    data_gift_st_msg: str = Field(..., alias="dataGiftStMsg", description="선물하기상태메세지")
    gift_psbl_cnt: str = Field(..., alias="giftPsblCnt", description="일반선물가능횟수")
    gift_psbl_qty: str = Field(..., alias="giftPsblQty", description="선물가능용량MB")
    fmly_gift_psbl_cnt: str = Field(..., alias="fmlyGiftPsblCnt", description="가족선물가능횟수")
    fmly_gift_psbl_qty: str = Field(..., alias="fmlyGiftPsblQty", description="가족선물가능용량MB")
    pen_aply_st_cd: str = Field(..., alias="penAplyStCd", description="선물제한상태코드")
    pen_aply_sta_dt: str = Field(..., alias="penAplyStaDt", description="선물제한시작일자")
    pen_aply_end_dt: str = Field(..., alias="penAplyEndDt", description="선물제한종료일자")
    adult_yn: str = Field(..., alias="adultYn", description="성인여부")
    fmly_yn: str = Field(..., alias="fmlyYn", description="가족결합여부")
    good_fmly_yn: str = Field(..., alias="goodFmlyYn", description="T가족결합여부")
    good_fmly_teen_shr_yn: str = Field(
        ..., alias="goodFmlyTeenShrYn", description="T가족결합_청소년공유여부"
    )
    blklst_st_cd: str = Field(..., alias="blklstStCd", description="블랙리스트상태코드")

    class Config:
        populate_by_name = True


class RegularDataGiftLimit(BaseModel):
    """정기 데이터 선물 한도 정보"""

    regu_data_gift_psbl_yn: str = Field(
        ..., alias="reguDataGiftPsblYn", description="자동선물하기가능여부"
    )
    regu_data_gift_st_cd: str = Field(
        ..., alias="reguDataGiftStCd", description="자동선물하기상태코드"
    )
    regu_data_gift_st_msg: str = Field(
        ..., alias="reguDataGiftStMsg", description="자동선물하기상태메세지"
    )
    regu_data_gift_lmt: str = Field(
        ..., alias="reguDataGiftLmt", description="자동데이터선물잔여횟수"
    )

    class Config:
        populate_by_name = True


class DataGiftSendHistoryItem(BaseModel):
    """데이터 선물 발송 이력 항목"""

    op_dtm: str = Field(..., alias="opDtm", description="처리일시")
    data_qty: str = Field(..., alias="dataQty", description="선물데이터MB")
    befr_svc_num: str = Field(..., alias="befrSvcNum", description="수혜자서비스번호")
    befr_cust_nm: str = Field(..., alias="befrCustNm", description="수혜자고객명")
    data_gift_typ_cd: str = Field(..., alias="dataGiftTypCd", description="데이터선물유형코드")

    class Config:
        populate_by_name = True


class DataGiftSendHistory(BaseModel):
    """데이터 선물 발송 이력 정보"""

    hst_yn: str = Field(..., alias="hstYn", description="이력여부")
    hst_cnt: str = Field(..., alias="hstCnt", description="총이력갯수")
    hst_list: List[DataGiftSendHistoryItem] = Field(
        default=[], alias="hstList", description="이력목록"
    )
    re_data_gift_psbl_yn: str = Field(
        ..., alias="reDataGiftPsblYn", description="다시데이터선물하기가능여부"
    )
    regu_data_gift_psbl_yn: str = Field(
        ..., alias="reguDataGiftPsblYn", description="자동선물하기가능여부"
    )

    class Config:
        populate_by_name = True


class DataGiftReceiver(BaseModel):
    """데이터 선물 수신자 정보"""

    data_gift_psbl_yn: str = Field(..., alias="dataGiftPsblYn", description="선물받기가능여부")
    data_gift_st_cd: str = Field(..., alias="dataGiftStCd", description="선물받기상태코드")
    data_gift_st_msg: str = Field(..., alias="dataGiftStMsg", description="선물받기상태메세지")
    same_fmly_grp_yn: str = Field(..., alias="sameFmlyGrpYn", description="동일가족결합그룹여부")
    same_good_fmly_grp_yn: str = Field(
        ..., alias="sameGoodFmlyGrpYn", description="동일T가족결합그룹여부"
    )

    class Config:
        populate_by_name = True


class RegularDataGiftReceiver(BaseModel):
    """정기 데이터 선물 수신자 정보"""

    regu_data_gift_psbl_yn: str = Field(
        ..., alias="reguDataGiftPsblYn", description="자동선물받기가능여부"
    )
    regu_data_gift_st_cd: str = Field(..., alias="reguDataGiftStCd", description="결과코드")
    regu_data_gift_st_msg: str = Field(
        ..., alias="reguDataGiftStMsg", description="자동선물받기상태메세지"
    )
    befr_cust_name: str = Field(..., alias="befrCustName", description="수혜자고객명")

    class Config:
        populate_by_name = True


class RefillCouponItem(BaseModel):
    """리필 쿠폰 항목"""

    copn_isue_num: str = Field(..., alias="copnIsueNum", description="쿠폰발급번호")
    copn_nm: str = Field(..., alias="copnNm", description="쿠폰명")
    copn_isue_dt: str = Field(..., alias="copnIsueDt", description="쿠폰발급일자")
    rfil_psbl_sta_dt: str = Field(..., alias="rfilPsblStaDt", description="리필가능시작일자")
    rfil_psbl_end_dt: str = Field(..., alias="rfilPsblEndDt", description="리필가능종료일자")

    class Config:
        populate_by_name = True


class DataRefillCoupon(BaseModel):
    """데이터 충전 쿠폰 정보"""

    rfil_psbl_yn: str = Field(..., alias="rfilPsblYn", description="리필가능여부")
    curr_rfil_psbl_yn: str = Field(..., alias="currRfilPsblYn", description="금월리필가능여부")
    rfil_psbl_itm: str = Field(..., alias="rfilPsblItm", description="리필가능항목")
    gift_psbl_yn: str = Field(..., alias="giftPsblYn", description="선물가능여부")
    fmly_comb_scrb_yn: str = Field(..., alias="fmlyCombScrbYn", description="가족결합가입여부")
    copn_isue_trgt_yn: str = Field(..., alias="copnIsueTrgtYn", description="쿠폰발급대상여부")
    copn_list: List[RefillCouponItem] = Field(default=[], alias="copnList", description="쿠폰목록")
    fst_ltrm_copn: RefillCouponItem = Field(..., alias="fstLtrmCopn", description="첫번째장기쿠폰")
    fst_gift_copn: RefillCouponItem = Field(..., alias="fstGiftCopn", description="첫번째선물쿠폰")

    class Config:
        populate_by_name = True
