from typing import List

from pydantic import BaseModel, Field


class DataUsage(BaseModel):
    """데이터 사용량 정보"""

    tot_data_usg_qty: str = Field(..., alias="totDataUsgQty", description="총데이터사용량MB")
    bas_ofr_data_qty: str = Field(..., alias="basOfrDataQty", description="기본제공데이터량MB")
    bas_ofr_data_usg_qty: str = Field(
        ..., alias="basOfrDataUsgQty", description="기본제공데이터사용량MB"
    )

    class Config:
        populate_by_name = True


class RecentUsage(BaseModel):
    """최근 사용량 정보"""

    data_usg: DataUsage = Field(..., alias="dataUsg", description="데이터사용정보")

    class Config:
        populate_by_name = True


class DataLimitItem(BaseModel):
    """데이터 한도 항목"""

    tot_ofr_data_qty: str = Field(..., alias="totOfrDataQty", description="총제공데이터량MB")
    usg_data_qty: str = Field(..., alias="usgDataQty", description="사용데이터량MB")
    rem_data_qty: str = Field(..., alias="remDataQty", description="잔여데이터량MB")
    data_typ_cd: str = Field(..., alias="dataTypCd", description="데이터유형코드")
    data_typ_nm: str = Field(..., alias="dataTypNm", description="데이터유형명")

    class Config:
        populate_by_name = True


class DataLimit(BaseModel):
    """데이터 한도 정보"""

    pps_yn: str = Field(..., alias="ppsYn", description="선불요금제여부")
    spcl_plan_yn: str = Field(..., alias="spclPlanYn", description="특수요금제여부")
    data_use_psbl_yn: str = Field(
        ..., alias="dataUsePsblYn", description="데이터사용가능요금제여부"
    )
    data_rfil_psbl_yn: str = Field(
        ..., alias="dataRfilPsblYn", description="데이터리필가능요금제여부"
    )
    data_gift_snd_psbl_yn: str = Field(
        ..., alias="dataGiftSndPsblYn", description="데이터선물제공가능요금제여부"
    )
    data_gift_rcv_psbl_yn: str = Field(
        ..., alias="dataGiftRcvPsblYn", description="데이터선물수혜가능요금제여부"
    )
    data_lmt_incld_yn: str = Field(..., alias="dataLmtIncldYn", description="데이터잔여량존재여부")
    yt_yn: str = Field(..., alias="ytYn", description="만34세미만여부")
    yt_data_chrg_psbl_yn: str = Field(
        ..., alias="ytDataChrgPsblYn", description="0데이터충전가능여부"
    )
    data_gift_psbl_yn: str = Field(..., alias="dataGiftPsblYn", description="데이터선물가능여부")
    chld_reg_yn: str = Field(..., alias="chldRegYn", description="자녀등록여부")
    tot_ofr_data_qty_sum: str = Field(..., alias="totOfrDataQtySum", description="총제공데이터량MB")
    usg_data_qty_sum: str = Field(..., alias="usgDataQtySum", description="사용데이터량MB")
    rem_data_qty_sum: str = Field(..., alias="remDataQtySum", description="잔여데이터량MB")
    rem_data_qty_rt: str = Field(..., alias="remDataQtyRt", description="잔여데이터상태")
    fee_prod_id: str = Field(..., alias="feeProdId", description="기본요금제ID")
    fee_prod_nm: str = Field(..., alias="feeProdNm", description="기본요금제명")
    fee_prod_ctt: str = Field(..., alias="feeProdCtt", description="기본요금제설명")
    fee_prod_chg_dt: str = Field(..., alias="feeProdChgDt", description="기본요금제변경일자")
    data_list: List[DataLimitItem] = Field(default=[], alias="dataList", description="데이터목록")

    class Config:
        populate_by_name = True


class ChildDataLimitItem(BaseModel):
    """자녀 데이터 한도 항목"""

    tot_ofr_data_qty: str = Field(..., alias="totOfrDataQty", description="총제공데이터량MB")
    usg_data_qty: str = Field(..., alias="usgDataQty", description="사용데이터량MB")
    rem_data_qty: str = Field(..., alias="remDataQty", description="잔여데이터량MB")
    prod_id: str = Field(..., alias="prodId", description="상품ID")
    prod_nm: str = Field(..., alias="prodNm", description="상품명")
    skip_id: str = Field(..., alias="skipId", description="공제항목ID")
    skip_nm: str = Field(..., alias="skipNm", description="공제항목명")

    class Config:
        populate_by_name = True


class ChildDataLimit(BaseModel):
    """자녀 데이터 한도 정보"""

    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="서비스관리번호")
    svc_num: str = Field(..., alias="svcNum", description="서비스번호")
    tot_ofr_data_qty: str = Field(..., alias="totOfrDataQty", description="총제공데이터량MB")
    usg_data_qty: str = Field(..., alias="usgDataQty", description="사용데이터량MB")
    rem_data_qty: str = Field(..., alias="remDataQty", description="잔여데이터량MB")
    data_list: List[ChildDataLimitItem] = Field(
        default=[], alias="dataList", description="데이터목록"
    )
    shr_data_list: List[ChildDataLimitItem] = Field(
        default=[], alias="shrDataList", description="공유데이터목록"
    )

    class Config:
        populate_by_name = True


class DataLimitChildren(BaseModel):
    """자녀 데이터 한도 정보"""

    chld_list: List[ChildDataLimit] = Field(default=[], alias="chldList", description="자녀목록")

    class Config:
        populate_by_name = True


class DataSharingService(BaseModel):
    """데이터 공유 서비스 정보"""

    svc_num: str = Field(..., alias="svcNum", description="(자)서비스번호")
    svc_mgmt_num: str = Field(..., alias="svcMgmtNum", description="(자)서비스관리번호")
    fee_prod_id: str = Field(..., alias="feeProdId", description="(자)상품ID")
    fee_prod_nm: str = Field(..., alias="feeProdNm", description="(자)상품명")

    class Config:
        populate_by_name = True


class DataSharingLimit(BaseModel):
    """데이터 공유 한도 정보"""

    data_shr_scrb_yn: str = Field(..., alias="dataShrScrbYn", description="데이터함께쓰기가입여부")
    data_shr_usg_data_qty: str = Field(
        ..., alias="dataShrUsgDataQty", description="데이터함께쓰기사용량MB"
    )
    data_shr_svc_list: List[DataSharingService] = Field(
        default=[], alias="dataShrSvcList", description="데이터함께쓰기서비스목록"
    )

    class Config:
        populate_by_name = True


class VoiceLimitItem(BaseModel):
    """음성 한도 항목"""

    tot_ofr_voice_qty: str = Field(..., alias="totOfrVoiceQty", description="총제공음성량분")
    usg_voice_qty: str = Field(..., alias="usgVoiceQty", description="사용음성량분")
    rem_voice_qty: str = Field(..., alias="remVoiceQty", description="잔여음성량분")
    prod_id: str = Field(..., alias="prodId", description="상품ID")
    prod_nm: str = Field(..., alias="prodNm", description="상품명")
    skip_id: str = Field(..., alias="skipId", description="공제항목ID")
    skip_nm: str = Field(..., alias="skipNm", description="공제항목명")

    class Config:
        populate_by_name = True


class VoiceLimit(BaseModel):
    """음성 한도 정보"""

    voice_rfil_psbl_yn: str = Field(..., alias="voiceRfilPsblYn", description="음성리필가능여부")
    chld_reg_yn: str = Field(..., alias="chldRegYn", description="자녀등록여부")
    tot_ofr_voice_qty_sum: str = Field(..., alias="totOfrVoiceQtySum", description="총제공음성량분")
    usg_voice_qty_sum: str = Field(..., alias="usgVoiceQtySum", description="사용음성량분")
    rem_voice_qty_sum: str = Field(..., alias="remVoiceQtySum", description="잔여음성량분")
    voice_list: List[VoiceLimitItem] = Field(default=[], alias="voiceList", description="음성목록")

    class Config:
        populate_by_name = True


class VoiceLimitChildren(BaseModel):
    """자녀 음성 한도 정보"""

    pass  # docstring에서 구체적인 필드 정보를 찾지 못했습니다


class TFamilySharingDataLimit(BaseModel):
    """T가족 공유 데이터 한도 정보"""

    pass  # docstring에서 구체적인 필드 정보를 찾지 못했습니다
