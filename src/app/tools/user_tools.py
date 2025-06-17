from langchain.tools import tool
from src.app.agents.utils import call_pe_tool_v2


@tool(parse_docstring=True)
def get_service_info(svc_mgmt_num: str):
    """
    Retrieves the customer's basic information, including mobile number (svcNum), subscription date (svcScrbDtm), birth date (ssnBirthDt), gender (ssnSexCd, where 1 = male, 2 = female), and subscribing product details such as product ID (feeProdId), product name (feeProdNm), subscription change date (feeProdChgDt), and device model (EqpMdlNm). 
    Detailed information about the customer's subscribed products is not included so it is necessary to call the 'prod_meta_search' tool to get the product details by the 'feeProdNm'.
    The customer's age is calculated from the birth date.

    Args:
        svc_mgmt_num (str): Customer's ID number(ex: '7022044239')

    Returns:
        dict: Retrived customer information
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
        "custNm": "익명1",
        "ctzCorpBizNum": "8209292000000",
        "ssnBirthDt": "950929",
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
    Retrieves the full list of products the customer is subscribed to, including mobile plans, bundled products, and additional services.

    Args:
        svc_mgmt_num (str): Customer's ID number(ex: '7022044239')

    Returns:
        list: Customer's subscribed products list and details.
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


@tool(parse_docstring=True)
def thinking_tool(query: str, current_step: str, past_steps: list):
    """
    지금까지 수집한 정보 기반으로 유저의 질의에 대한 생각을 정리합니다.

    Args:
        query (str): 유저의 질의
        current_step (str): 현재 수행할 단계
        past_steps (list): 지금까지 수행한 단계

    Returns:
        str: 현재 단계에 대한 생각
    """
    prompt_str = f"""
    유저 질의: {query}
    지금까지 수행한 단계: {past_steps}
    현재 수행할 단계: {current_step}

    현재 단계에 대한 생각을 정리해주세요.
    """
    response = call_pe_tool_v2(system_message=prompt_str, tools=[])
    return response.content
