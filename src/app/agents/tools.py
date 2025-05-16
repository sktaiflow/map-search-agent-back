from langchain.tools import tool
import pprint

def tool_to_openai_function(tool_obj):
    args = tool_obj.args
    properties = {}
    required = []
    for k, v in args.items():
        properties[k] = {
            "type": v.get("type"),
            "description": v.get("description"),
        }
        if "default" not in v or v["default"] is None:
            required.append(k)
    return {
        "type": "function",
        "function": {
            "name": tool_obj.name,
            "description": tool_obj.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False
            }
        },
        "strict": True
    }

@tool(parse_docstring=True)
def prod_meta_search(query: str):
    """
    SKT 에서 제공하는 요금제, 부가서비스, 로밍, 혜택 상품에 대한 상세 검색 결과를 제공합니다.

    Args:
        query (str): 검색할 상품 메타 정보

    Returns:
        dict: 검색 결과
    """
    # TODO : 실제 데이터 조회 후 반환
    return {
            "productId": {
                "value": "PA00000066"
            },
            "statusOfOperation": {
                "value": "운영"
            },
            "classifiedGroup": {
                "value": "상품 > 기본요금제 > 휴대폰 요금제"
            },
            "productName": {
                "value": "5GX 프라임플러스(넷플릭스)"
            },
            "productNameInEnglish": {
                "value": "5GX Prime Plus(Netflix)"
            },
            "lineup": {
                "value": "넷플릭스 요금제"
            },
            "marketingKeyword": {
                "valueList": [
                    "넷플릭스",
                    "우주패스Netflix",
                    "Netflix",
                    "넷플릭스할인",
                    "5GX플랜",
                    "혜택요금제",
                    "wavve혜택",
                    "OTT혜택",
                    "넷플릭스혜택",
                    "Wavve",
                    "스트리밍",
                    "태블릿요금무료혜택",
                    "스마트워치요금무료혜택",
                    "VIP멤버십혜택"
                ]
            },
            "generation": {
                "valueList": [
                    "LTE generation",
                    "5G generation"
                ]
            },
            "approvalInfo": {
                "value": "요금팀/이상희"
            },
            "productOperationPeriod": {
                "value": "2024.06.27~9999.12.31"
            },
            "mappedProductCode": {
                "productCode": {
                    "valueList": [
                        "NA00008721"
                    ]
                }
            },
            "monthlyPrice": {
                "monthlyPrice": {
                    "value": "99000원"
                },
                "monthlyPriceWithoutVAT": {
                    "value": "90000원"
                },
                "monthlyPriceWithSelectableInstallment": {
                    "value": "74250원"
                },
                "billingMethod": {
                    "value": "후불"
                }
            },
            "versionInfo": {
                "value": "1.0"
            },
            "productDescription": {
                "value": "무제한 데이터와 넷플릭스 멤버십을 제공하는 넷플릭스 전용 요금제"
            },
            "productSubscriptionCondition": {
                "value": "19세 이상 성인, 고객 명의당 1개만 가입 가능"
            },
            "productRequiredNotice": {},
            "productSubscriptionMethod": {
                "value": "고객센터, 대리점, T월드 가입 가능"
            }
        }

@tool(parse_docstring=True)
def get_service_info(svc_mgmt_num: str):
    """
    가입된 고객의 기본 신상정보(svcNum - 휴대폰 번호, svcScrbDtm - 가입날짜, ssnBirthDt - 생년월일, ssnSexCd - 성별 정보(2: 여자, 1: 남자)) 및 가입상품 정보(feeProdId - 상품ID, feeProdNm - 상품명, feeProdChgDt - 상품변경일자, EqpMdlNm - 단말기 모델명)를 조회합니다.

    Args:
        svc_mgmt_num (str): 조회할 서비스관리번호(예: '7022044239')

    Returns:
        dict: 요청한 정보 유형에 따른 서비스/청구/고객 정보
    """
    # 실제 API 호출 대신 데모 데이터를 반환
    # 실제 구현에서는 API를 호출하여 데이터를 가져와야 함
    return {
        "svcMgmtNum": "7022044239",
        "svcNum": "01094793421",
        "svcCd": "C",
        "svcStCd": "AC",
        "svcStChgCd": "I1",
        "svcChgRsnCd": "02",
        "svcTypCd": "01",
        "svcScrbDtm": "20231218",
        "scrbReqRsnCd": "02",
        "wlfDcCd": "",
        "estationAgreeYn": "N",
        "feeProdId": "NA00007790",
        "feeProdNm": "5GX 프라임",
        "feeProdChgDt": "20230104",
        "eqpMdlCd": "A3UU",
        "eqpMdlNm": "SM-S901NW",
        "eqpSerNum": "0065549",
        "eqpUsgCd": "W",
        "eqpMthdCd": "F",
        "eqpMktgDt": "20220210",
        "nwMthdCd": "13",
        "custNum": "9252302408",
        "custNm": "이재환",
        "ctzCorpBizNum": "8209292000000",
        "ssnBirthDt": "820929",
        "ssnSexCd": "2",
        "custTypCd": "01",
        "custDtlTypCd": "N0",
        "acntNum": "6425211166",
        "acntTypCd": "01",
        "payMthdCd": "01",
    }
@tool(parse_docstring=True)
def get_subscribed_products(svc_mgmt_num: str = None):
    """
    고객이 가입되어 모든 상품 목록을 조회합니다. 상품에는 요금제, 결합상품, 부가서비스 등이 포함됩니다.

    Args:
        svc_mgmt_num (str): 조회할 서비스관리번호(예: '7022044239')

    Returns:
        list: 고객의 가입상품 목록 및 상세 정보
    """
    # 실제 API 호출 대신 데모 데이터를 반환
    # 실제 구현에서는 API를 호출하여 데이터를 가져와야 함
    return [
        {
            "svcMgmtNum": "7022044239",
            "scrbProdList": [
                {
                    "prodId": "NA00007790",
                    "prodNm": "5GX 프라임",
                    "svcProdCd": "1",
                    "scrbDt": "20240101",
                },
                {
                    "prodId": "NH00000157",
                    "prodNm": "요즘가족결합",
                    "svcProdCd": "2",
                    "scrbDt": "20240101",
                },
                {
                    "prodId": "NA00000262",
                    "prodNm": "소리샘",
                    "svcProdCd": "3",
                    "scrbDt": "20240101",
                },
            ],
        }
    ]