
CYPHER_CORRECTION_TEMPLATE = """Task:Re-generate Cypher statement to query a graph database.
    Instructions:
    The previous Cypher query was inappropriate or did not return any results.
    Modify the Cypher query to ensure it returns relevant results based on the provided schema and the user's question.
    You can modify the main keywords by removing symbols, split by spaces, or using synonyms.
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided in the schema.
    Korean terms should be surrounded by backticks (``).
    Limit the number of results to 10.

    Schema:
    {schema}

    Domain mapping and other rules:
    - For 기본제공데이터용량 (data limit), 문자기본제공량 (sms limit), 기본음성제공통화량 (voice limit) and similar numeric fields, treat the term 무제한 (unlimited) as the value 99999. Do not apply this rule to price fields.
    - For age-related queries, check whether the given age is within the range defined by 최소나이 (minimum age) and 최대나이 (maximum age).
    - For questions about cheap or expensive plans, sort by the value of VAT포함월정액 (VAT included monthly price).
    - For finding benefits or offers, focus primarily on the 마케팅키워드 (marketing keywords) nodes and 상품설명 (product description) fields.
    - To handle list type properties, use following style cypher: ANY(item IN node.list_property WHERE item CONTAINS "keyword")
    - For search keywords, prefer single nouns without spaces. For example, use "넷플릭스" instead of "넷플릭스 할인".
    - For questions about available plans, also retrieve whether the user is eligible to subscribe by checking the 상품가입조건 (productsubscriptioncondition).
    - For comparing products, generate a Cypher query that retrieves all products to be compared, and then compare the results.
    - Do not try to matching 마케팅키워드 (marketing keywords) from the label itself. Must use the properties of the nodes to match keywords. Not "k = 'keyword'". Do "k.`값` CONTAINS 'keyword'.

    For querying list properties, do not use the CONTAINS operator directly on the array itself.
    Instead, use one of the following methods depending on the query intent:
    - To check for exact inclusion of a value: "value" IN node.array_property
    - To check if any element partially matches a condition (e.g., substring): ANY(item IN node.array_property WHERE item CONTAINS "value")
    - To check if all elements satisfy a condition: ALL(item IN node.array_property WHERE item CONTAINS "value")

    Results should be grouped by 요금제 (mobile plan) and collect other related nodes as a list.
    - MATCH (p:`요금제`)-[:`가입해지조건`]->(benefit:`혜택`) WITH p, COLLECT(benefit) AS benefits RETURN p, benefits LIMIT 10

    Example:
    - "18세 미만만 가입할 수 있는 요금제 알려줘" -> "MATCH (p:`요금제`)-[:`최대가입가능나이`]->(maxAge:`최대나이`) WHERE maxAge.`값` < 18 RETURN p, maxAge"
    - "5GX 프리미엄 요금제와 가격이 비슷한 요금제 비교해줘" -> "MATCH (p:`요금제` {{`상품명`: '5GX 프리미엄'}}) WITH p, p.`VAT포함월정액` AS reference_price MATCH (other:`요금제`) WHERE ABS(other.`VAT포함월정액` - reference_price) <= reference_price * 0.2 RETURN p AS `기준상품`, other AS `유사상품` ORDER BY ABS(other.`VAT포함월정액` - reference_price)"
    - "데이터 무제한 요금제 하나만 알려줘" -> "MATCH (p:`요금제`)-[:`기본제공데이터용량`]->(data:`기본제공데이터용량`) WHERE data.`값` = 99999 RETURN p, data LIMIT 1"

    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.
    If there are keywords used in the cypher, include the nodes related to those keywords in the result.

    The inappropriate previous Cypher query was:
    {previous_cypher}

    The question is:
    {question}
"""

CYPHER_CORRECTION_PROMPT = PromptTemplate(
    input_variables=["schema", "question", "previous_cypher"],
    template=CYPHER_CORRECTION_TEMPLATE,
)

CYPHER_QA_TEMPLATE = """You are a product specialist in SK Telecom helps to form nice and human understandable answers in Korean.
    The Information part contains the provided information that you must use to construct an answer.
    The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
    Make the answer sound as a response to the question. Do not mention that you based the result on the given information.
    Answer should contains 상품명 (product name), 상품설명 (product description), VAT포함월정액 (monthlyprice), 최대 가입가능 나이 및 최소 가입가능 나이 (minimum age and maximum age).
    If there are more than one product, use top 10 products and the result should be a markdown table.
    Do not mention that how you can subscribe to the product.
    Here is an example:

    Question: 데이터 무제한 요금제 하나만 알려줘
    Context:'상품설명': '무제한 데이터와 0청년 특화 혜택 외 디즈니 플러스 멤버십을 제공하는 디즈니 플러스 전용 요금제로 SK텔레콤 공식 온라인 채널인 T다이렉트샵에서 만 19세 이상 34세 이하 개인 고객만 가입 가능한 온라인 전용 무약정 요금제', '라인업': '0청년 다이렉트 디즈니+ 요금제', '상품명': '0 청년 다이렉트 69(디즈니+)', 'VAT포함월정액': 69000
    Helpful Answer: 데이터 무제한 요금제에는 0 청년 다이렉트 69(디즈니+)가 있고, 해당 요금제의 월정액 요금은 69,000원입니다. 해당 요금제는 무제한 데이터 외에 0청년 특화 혜택과 디즈니 플러스 멤버십을 제공하며, 만 19세 이상 34세 이하 개인 고객만 가입이 가능한 온라인 전용 무약정 요금제입니다.

    Follow this example when generating answers.
    If the provided information is empty, say that you don't know the answer.
    Information:
    {context}

    Question: {question}
    Helpful Answer:
"""

CYPHER_QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"], template=CYPHER_QA_TEMPLATE
)
