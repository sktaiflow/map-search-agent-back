import re
from langchain_openai import ChatOpenAI
from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
import json

# llm 연결 
custom_base_url = "https://aihub-api.sktelecom.com/aihub/v2/sandbox"
api_key = "e97ee307-a791-4e06-ade1-df4b9d032eed" ############ 지우고커밋!!!!!! 
llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_base=custom_base_url,
    openai_api_key=api_key
)

# 최신 Neo4jGraph 객체 생성
graph = Neo4jGraph(
    url="bolt://neo4j-gds-apoc-n10s:7687",
    username="neo4j",
    password="neo4jpassword"
)

# QA Chain 준비
qa_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True,
    allow_dangerous_requests=True
)

def clean_cypher(cypher_text: str) -> str:
    """
    Remove ```cypher and ``` if present.
    """
    # Remove ```cypher and ``` markers
    cleaned = re.sub(r"^```cypher\s*", "", cypher_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
    return cleaned.strip()

def search_neo4j(user_query: str, metadata: dict) -> dict:
    """
    사용자 질문에 대해:
    - Cypher 쿼리 생성
    - Neo4j 쿼리 실행
    - 결과 요약
    """
    # Cypher 쿼리 생성
    schema_text = graph.get_schema

    generation_prompt = f"""
        아래의 질문에 대해 Cypher 쿼리를 작성하세요.
        
        조건:
        - 긴 문구를 그대로 사용하지 마시고, 질문에서 핵심 단어를 추출해 매칭 조건에 사용하세요. (예: "무제한 데이터 요금제" → "무제한")
        - 상품설명(y.상품설명)과 마케팅키워드(y.마케팅키워드) 속성을 WHERE 조건에 우선적으로 활용하세요.
        - 불필요하게 많은 OPTIONAL MATCH는 작성하지 마시고, 필요한 정보만 RETURN 하세요.
        - Cypher 쿼리를 마크다운 코드블럭으로 반환하세요. (```cypher ... ```)
        
        질문:
        {user_query}
    """
    
    raw_cypher = qa_chain.cypher_generation_chain.run({
        "question": generation_prompt,
        "schema": schema_text
    })

    # 마크다운 제거
    cypher_query = clean_cypher(raw_cypher)
    cypher_query = cypher_query.strip()
    print(f"[search_neo4j] {cypher_query}")
    
    # Neo4j 실행
    try:
        records = graph.query(cypher_query)
    except Exception as e:
        print(f"❌ Neo4j 쿼리 실행 실패: {e}")
        return {
            "cypher_query": cypher_query,
            "raw_records": [],
            "error": str(e)
        }
    
    # 결과 요약
    MAX_RECORDS = 20
    sampled_records = records[:MAX_RECORDS]

    summary_prompt = f"""
        아래에 Neo4j 쿼리 결과 샘플 {MAX_RECORDS}건이 있습니다.
        
        이 샘플을 참고하여 **사용자의 질문 의도와 기대하는 답변에 부합하는 상세한 설명과 추천**을 생성하세요.
        
        아래 정보에 반드시 기반하세요:
        - User Intent: {metadata["intent"]}
        - Paraphrased Query: {metadata["paraphrased_query"]}
        - Expected Answer: {metadata["expected_answer"]}
        
        질문에 맞는 요금제의 특징, 가격, 데이터 용량, 가입 조건을 구체적으로 설명하고, 
        유사 요금제를 비교하며, 사용자가 쉽게 선택할 수 있도록 추천과 결론까지 포함하세요.
        
        (전체 데이터가 너무 커서 일부만 제공됩니다.)
        
        User query:
        {user_query}
        
        Cypher Query:
        {cypher_query}
        
        Query Result Sample:
        {sampled_records}
    """

    summary_response = llm.invoke([
        {"role": "system", "content": "You are a skilled summarizer."},
        {"role": "user", "content": summary_prompt}
    ])

    summary_text = summary_response.content.strip()

    with open("search_neo4j_log.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "user_query": user_query,
            "cypher_query": cypher_query,
            "records": records,
            "summary_prompt": summary_prompt,
            "summary_text": summary_text
        }, ensure_ascii=False) + "\n")
    
    return {
        "user_query": user_query,
        "cypher_query": cypher_query,
        "raw_records": records,
        "summary": summary_text
    }

def get_service_info(svc_mgmt_num: str):
    """
    가입된 고객의 기본 신상정보(svcNum - 휴대폰 번호, svcScrbDtm - 가입날짜, ssnBirthDt - 생년월일, ssnSexCd - 성별 정보(2: 여자, 1: 남자)) 및 가입상품 정보(feeProdId - 상품ID, feeProdNm - 상품명, feeProdChgDt - 상품변경일자, EqpMdlNm - 단말기 모델명)를 조회합니다. 나이 정보는 생년월일을 통해 계산합니다.

    Args:
        svc_mgmt_num (str): 조회할 서비스관리번호(예: '7022044239')

    Returns:
        dict: 요청한 정보 유형에 따른 서비스/청구/고객 정보
    """
    # 실제 API 호출 대신 데모 데이터를 반환
    # 실제 구현에서는 API를 호출하여 데이터를 가져와야 함

    api_response = {
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
    # 의미 있게 사용될 필드만 남김 
    keys_to_keep = ['svcMgmtNum', 'svcNum', 'feeProdId', 'feeProdNm', 'feeProdChgDt', 'ssnBirthDt', 'ssnSexCd']
    api_response = {k: v for k, v in api_response.items() if k in keys_to_keep}
    
    mapping_dict = {
        "svcMgmtNum": "서비스관리번호(String)",
        "svcNum": "서비스번호(String)",
        "svcCd": "서비스구분코드(String)",
        "svcStCd": "서비스상태코드(String)",
        "svcStChgCd": "서비스상태변경코드(String)",
        "svcChgRsnCd": "서비스변경사유코드(String)",
        "svcTypCd": "서비스이용종류코드(String)",
        "svcScrbDtm": "서비스가입일자(String)",
        "scrbReqRsnCd": "가입신청사유코드(String)",
        "wlfDcCd": "복지할인유형코드(String)",
        "estationAgreeYn": "웹회원신청동의여부(String)",
        "feeProdId": "요금상품ID(String)",
        "feeProdNm": "요금상품명(String)",
        "feeProdChgDt": "요금제변경일자(String)",
        "eqpMdlCd": "단말기모델코드(String)",
        "eqpMdlNm": "단말기모델명(String)",
        "eqpSerNum": "단말기일련번호(String)",
        "eqpUsgCd": "단말기용도코드(String)",
        "eqpMthdCd": "단말기방식코드(String)",
        "eqpMktgDt": "단말기출시일자(String)",
        "nwMthdCd": "네트워크방식코드(String)",
        "custNum": "고객번호(String)",
        "custNm": "고객명(String)",
        "ctzCorpBizNum": "주민번호사업자등록번호(String)",
        "ssnBirthDt": "생년월일(String)",
        "ssnSexCd": "성별코드(String)",
        "custTypCd": "고객유형코드(String)",
        "custDtlTypCd": "고객세부유형코드(String)",
        "age": "고객나이(String)",
        "acntNum": "계정번호(String)",
        "acntTypCd": "계정유형코드(String)",
        "payMthdCd": "납부방법코드(String)",
    }

    result = {}
    for k, v in api_response.items():
        # 매핑 dict에 키가 있으면 한글명 사용
        translated_key = mapping_dict.get(k, k)
        result[translated_key] = v
    return result

def translate_keys_recursive(obj, mapping_dict):
    """
    중첩 딕셔너리/리스트에 대해 key를 매핑 dict로 치환하는 재귀 함수
    """
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            translated_key = mapping_dict.get(k, k)
            new_dict[translated_key] = translate_keys_recursive(v, mapping_dict)
        return new_dict
    elif isinstance(obj, list):
        return [translate_keys_recursive(item, mapping_dict) for item in obj]
    else:
        return obj

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

    api_response = [
        {
            "svcMgmtNum": "7022044239",
            "svcNum": "01088600160",
            "scrbProdList": [
                {
                    "prodId": "NA00007790",
                    "prodNm": "5GX 프라임",
                    "svcProdCd": "1",
                    "scrbDt": "20240101"
                },
                {
                    "prodId": "NH00000157",
                    "prodNm": "요즘가족결합",
                    "svcProdCd": "2",
                    "scrbDt": "20240101"
                },
                {
                    "prodId": "NA00000262",
                    "prodNm": "소리샘",
                    "svcProdCd": "3",
                    "scrbDt": "20240101"
                }
            ]
        }
    ]

    mapping_dict = {
        "svcMgmtNum": "서비스관리번호(String)", 
        "svcNum": "서비스번호(String)", 
        "scrbProdList": "가입상품목록(List)",
        "prodId": "상품ID(String)",
        "prodNm": "상품명(String)",
        "svcProdCd": "서비스상품구분코드(String)",
        "scrbDt": "가입일자(String)",
        "scrbDcList": "할인목록(List)",
        "dcId": "할인ID(String)",
        "dcNm": "할인명(String)",
        "effStaDtm": "할인적용일시(String)"
    }

    translated = translate_keys_recursive(api_response, mapping_dict)
    return translated