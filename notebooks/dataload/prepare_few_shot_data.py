import os
import re
from typing import List

import pandas as pd


def extract_domain_tags(nl_text: str, cypher_query: str) -> List[str]:
    """자연어와 Cypher에서 도메인 태그 추출"""
    tags = []
    
    # 자연어 기반 태그
    if re.search(r'(\d+세|나이|연령|미만|이상|이하)', nl_text):
        tags.append('age')
    if re.search(r'(요금|금액|원|가격|비용|만원|싸게)', nl_text):
        tags.append('pricing')
    if re.search(r'(데이터|기가|무제한|GB)', nl_text):
        tags.append('data')
    if re.search(r'(혜택|할인|서비스|무료)', nl_text):
        tags.append('benefits')
    if re.search(r'(VIP|멤버십|등급)', nl_text):
        tags.append('membership')
    if re.search(r'(비교|비슷|차이|가장)', nl_text):
        tags.append('comparison')
    if re.search(r'(아이패드|태블릿|스마트워치|기기)', nl_text):
        tags.append('device')
    if re.search(r'(5GX|티플랜|0플랜|베이직플러스|프리미엄) (요금제|알려|정보)', nl_text):
        tags.append('specific_plan')
    
    # Cypher 기반 태그
    if '가입조건' in cypher_query:
        tags.append('age_condition')
    if 'ORDER BY' in cypher_query:
        tags.append('sorting')
    if 'LIMIT' in cypher_query:
        tags.append('limited_result')
    if 'COUNT' in cypher_query:
        tags.append('aggregation')
    if 'OPTIONAL MATCH' in cypher_query:
        tags.append('optional_data')
    
    return list(set(tags))  # 중복 제거

def calculate_initial_quality(nl_text: str, cypher_query: str) -> float:
    """초기 품질 점수 계산"""
    quality = 1.0
    
    # 자연어 품질 체크
    if len(nl_text.strip()) < 5:
        quality -= 0.3
    elif len(nl_text.strip()) < 10:
        quality -= 0.1
    
    # 질문 형태 체크
    if not ('?' in nl_text or '요' in nl_text or '까' in nl_text or '나요' in nl_text):
        quality -= 0.1
    
    # Cypher 품질 체크
    if 'RETURN' not in cypher_query.upper():
        quality -= 0.5
    
    # 특수문자 체크 (오타 가능성)
    special_chars = len(re.findall(r'[^\w\s가-힣`\-\[\]():.,?!\'"]', nl_text))
    if special_chars > 0:
        quality -= min(0.2, special_chars * 0.05)
    
    # 복잡한 쿼리는 품질 보너스
    if any(keyword in cypher_query.upper() for keyword in ['WITH', 'OPTIONAL', 'ORDER BY']):
        quality += 0.1
    
    return max(0.3, min(1.0, quality))

# 원본 데이터
raw_data = [
    ("18세 미만만 가입할 수 있는 요금제가 있어?", "MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최대나이` < 18 AND c.`가입가능최소나이` < 18 RETURN p, c"),
    ("5GX 프리미엄 요금제와 비슷한 요금의 요금제 비교해줘", "MATCH (p:`요금제` {`상품명`: '5GX 프리미엄'}) WITH p, p.`월정액` AS reference_price  MATCH (other:`요금제`) WHERE ABS(other.`월정액` - reference_price) <= reference_price * 0.1 RETURN p AS `기준상품`, other AS `유사상품` ORDER BY ABS(other.`월정액` - reference_price)"),
    ("무제한 데이터 요금제 하나 알려줘", "MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` = 99999 RETURN p, d LIMIT 1"),
    ("65세 이상이면 요금 할인혜택 없나요", "MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최소나이` >= 65 OPTIONAL MATCH (p)-[:`제공혜택`]->(h:`혜택`) RETURN p, c, h"),
    ("실버요금제", "MATCH (p:`요금제`)-[:`연관`]->(c:`개념`) WHERE c.`키워드` = '실버요금제' RETURN p, c"),
    ("내 요금제로 스마트기기 쓸 수 있어?", "MATCH (p:`요금제` {`상품명`: '5GX 프라임'})-[:`제공혜택`]->(c:`혜택`) WHERE c.`혜택명` CONTAINS '스마트워치'  OR c.`혜택명` CONTAINS '태블릿' RETURN p, c"),
    ("데이터 무제한이고 10만원 미만인 요금제 중 만40세인 사람이 사용할 수 있는 요금제 알려줘", "MATCH (p:`요금제`)-[:제공]->(d:`데이터용량`) MATCH (p)-[:`가입조건`]-(c:`가입조건`) WHERE d.`기본제공데이터용량` = 99999 AND p.`월정액` < 100000 AND c.`가입가능최대나이` >= 40 AND c.`가입가능최소나이` <= 40 RETURN p"),
    ("19세이하 요금제", "MATCH (p:`요금제`)-[:`가입조건`]->(a:`가입조건`) WHERE a.`가입가능최대나이` <= 19 AND a.`가입가능최소나이` <= 19 RETURN p, a"),
    ("데이터를 사용한만큼 금액을 내는 요금제는 없어?", "MATCH (p:`요금제`)-[:`연관`]->(c:`개념`) WHERE c.`키워드` = '종량제요금제' RETURN p, c"),
    ("데이터 30기가면 될 것 같은데 내가 가입가능한 요금제가 뭐가 있을까?", "MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` >= 30 ORDER BY d.`기본제공데이터용량` ASC LIMIT 3 RETURN p, d"),
    ("요금제에 음악 듣기 서비스가 되는 요금제가 있나요", "MATCH (p:`요금제`)-[]->(n:`개념`) WHERE n.`키워드` CONTAINS '음악듣기요금제' RETURN p, n"),
    ("멤버십 VIP 시켜주는 요금제 중 가장 제공 혜택 개수가 많은 요금제는 뭐야?", "MATCH (p:`요금제`)-[:`제공혜택`]->(h:`혜택`) WHERE h.`혜택명` CONTAINS 'VIP' WITH p MATCH (p)-[:`제공혜택`]->(b:`혜택`) WITH p, COUNT(b) AS b_count ORDER BY b_count DESC RETURN p, b_count"),
    ("우주패스 할인율 제일 크게 주는 요금제가 뭐야?", "MATCH (p:`요금제`)-[:`제공혜택`]->(h:`혜택`) WHERE h.`혜택명` CONTAINS '우주패스' ORDER BY h.`최대할인금액` DESC RETURN p, h LIMIT 1"),
    ("65세 이상 요금 할인 혜택 알려줘", "MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최소나이` >= 65 OPTIONAL MATCH (p)-[:`제공혜택`]->(h:`혜택`) RETURN p, h"),
    ("FLO 제일 싸게 쓰려면 어떻게 해야해?", "MATCH (h:`혜택`) WHERE h.`혜택명` = 'FLO 무료' ORDER BY h.`최대할인금액` DESC LIMIT 1 WITH h MATCH (p:`요금제`)-[]->(h) ORDER BY p.`월정액` ASC RETURN p, h"),
    ("무제한 데이터 혜택 요금제", "MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` = 99999 RETURN p"),
    ("베이직플러스로 변경 시 T가족모아데이터 이용 가능한가요?", "MATCH (p:요금제)-[r]->(b:혜택) WHERE b.혜택명 = 'T가족모아데이터'  AND p.상품명 = '베이직플러스' RETURN p, r, b"),
    ("39,000원 요금제 데이터 무제한인가요", "MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE p.`월정액` = 39000 RETURN p, d"),
    ("데이터 무제한, 통화 무제한 요금제 알려주세요", "MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) MATCH (p:`요금제`)-[:`제공`]->(c:`음성통화`) WHERE d.`기본제공데이터용량` = 99999 AND c.`음성통화제공량` = 99999 RETURN p, d, c"),
    ("SKT 표준 요금제도 T끼리 데이터선물 받을 수 있어?", "MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE p.`상품명` CONTAINS '표준' RETURN p, d"),
    ("아이패드 회선 무료 이용 요금제", "MATCH (p:`요금제`) WHERE ANY(k IN p.`마케팅키워드` WHERE k CONTAINS '태블릿요금무료') RETURN p"),
    ("키즈 요금제에서 MMS 사용료가 있나요?", "MATCH (p:`요금제`)-[:`제공`]->(m:`문자메시지`) WHERE ANY(keyword IN p.`마케팅키워드` WHERE keyword CONTAINS '키즈') RETURN p, m"),
    ("시니어요금제", "MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최소나이` >= 65 RETURN p, c"),
    ("자녀요금제는어떤것들이있나요?", "MATCH (p:`요금제`)-[:`가입조건`]->(c:`가입조건`) WHERE c.`가입가능최대나이` <= 18 RETURN p"),
    ("VIP 되려면 0청년 59 요금제 쓰면 돼?", "MATCH (p:`요금제`)-[r:`제공혜택`]->(n:`혜택` {`혜택명`:'T멤버십 VIP'}) WHERE p.`상품명` CONTAINS '0 청년' AND p.`상품명` CONTAINS '59' RETURN p, n"),
    # 특정 요금제명 검색 예시들 (상품명 우선 검색)
    ("5GX 프리미엄 요금제 알려줘", "MATCH (p:`요금제`) WHERE p.`상품명` CONTAINS '5GX 프리미엄' RETURN p"),
    ("티플랜 요금제 정보", "MATCH (p:`요금제`) WHERE p.`상품명` CONTAINS '티플랜' OR ANY(keyword IN p.`마케팅키워드` WHERE keyword CONTAINS '티플랜') RETURN p"),
    ("0플랜 알려줘", "MATCH (p:`요금제`) WHERE p.`상품명` CONTAINS '0플랜' OR ANY(keyword IN p.`마케팅키워드` WHERE keyword CONTAINS '0플랜') RETURN p"),
    ("베이직플러스 요금제", "MATCH (p:`요금제`) WHERE p.`상품명` CONTAINS '베이직플러스' RETURN p"),
    ("다이렉트5G 요금제는 뭐야?", "MATCH (p:`요금제`) WHERE p.`상품명` CONTAINS '다이렉트5G' RETURN p"),
    ("0틴플랜 종류 알려줘", "MATCH (p:`요금제`) WHERE p.`상품명` CONTAINS '0틴플랜' RETURN p")
]

# 데이터 처리
processed_data = []
for nl_text, cypher_query in raw_data:
    domain_tags = extract_domain_tags(nl_text, cypher_query)
    quality_score = calculate_initial_quality(nl_text, cypher_query)
    
    processed_data.append({
        'natural_language': nl_text,
        'cypher_query': cypher_query,
        'domain_tags': domain_tags,
        'quality_score': quality_score
    })

# CSV 파일 생성
df = pd.DataFrame(processed_data)
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'few_shot_data.csv')
df.to_csv(csv_path, index=False, encoding='utf-8')
print(f"✅ CSV 파일 생성 완료! {len(df)}개 레코드")
print(f"평균 품질 점수: {df['quality_score'].mean():.3f}")
print(f"도메인 태그 분포:")
all_tags = []
for tags in df['domain_tags']:
    all_tags.extend(eval(tags) if isinstance(tags, str) else tags)
from collections import Counter

print(Counter(all_tags))