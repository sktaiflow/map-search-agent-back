from langchain.tools import tool


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
        "productId": {"value": "PA00000066"},
        "statusOfOperation": {"value": "운영"},
        "classifiedGroup": {"value": "상품 > 기본요금제 > 휴대폰 요금제"},
        "productName": {"value": "5GX 프라임플러스(넷플릭스)"},
        "productNameInEnglish": {"value": "5GX Prime Plus(Netflix)"},
        "lineup": {"value": "넷플릭스 요금제"},
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
                "VIP멤버십혜택",
            ]
        },
        "generation": {"valueList": ["LTE generation", "5G generation"]},
        "approvalInfo": {"value": "요금팀/이상희"},
        "productOperationPeriod": {"value": "2024.06.27~9999.12.31"},
        "mappedProductCode": {"productCode": {"valueList": ["NA00008721"]}},
        "monthlyPrice": {
            "monthlyPrice": {"value": "99000원"},
            "monthlyPriceWithoutVAT": {"value": "90000원"},
            "monthlyPriceWithSelectableInstallment": {"value": "74250원"},
            "billingMethod": {"value": "후불"},
        },
        "versionInfo": {"value": "1.0"},
        "productDescription": {
            "value": "무제한 데이터와 넷플릭스 멤버십을 제공하는 넷플릭스 전용 요금제"
        },
        "productSubscriptionCondition": {"value": "19세 이상 성인, 고객 명의당 1개만 가입 가능"},
        "productRequiredNotice": {},
        "productSubscriptionMethod": {"value": "고객센터, 대리점, T월드 가입 가능"},
    }
