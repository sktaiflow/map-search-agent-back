#!/usr/bin/env python3
"""
Neo4j DB에서 상품설명과 기본제공데이터용량이 일치하지 않는 요금제를 찾는 스크립트
"""

import re
from neo4j import GraphDatabase
import os

# Neo4j 연결 설정
driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "neo4jpassword")
)

def extract_data_from_description(description):
    """상품설명에서 데이터 용량 추출"""
    if not description:
        return None
    
    # 패턴들
    patterns = [
        r'매월\s*(\d+(?:\.\d+)?)\s*GB',
        r'월\s*(\d+(?:\.\d+)?)\s*GB',
        r'(\d+(?:\.\d+)?)\s*GB\s*데이터',
        r'데이터\s*(\d+(?:\.\d+)?)\s*GB',
        r'무제한\s*데이터',
        r'데이터를\s*무제한',
    ]
    
    # 무제한 데이터 체크
    if '무제한' in description and '데이터' in description:
        return 99999.0
    
    # 숫자 추출
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match and pattern != r'무제한\s*데이터' and pattern != r'데이터를\s*무제한':
            return float(match.group(1))
    
    return None

def check_data_mismatches():
    """데이터 불일치 요금제 확인"""
    mismatches = []
    
    with driver.session() as session:
        # 모든 요금제 데이터 가져오기
        result = session.run("""
            MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`)
            RETURN p.`상품명` as name, p.`상품설명` as description, d.`기본제공데이터용량` as db_data
            ORDER BY p.`상품명`
        """)
        
        for record in result:
            name = record["name"]
            description = record["description"]
            db_data = float(record["db_data"]) if record["db_data"] else 0.0
            
            # 상품설명에서 데이터 추출
            desc_data = extract_data_from_description(description)
            
            if desc_data is not None:
                # 데이터가 일치하지 않는 경우
                if abs(desc_data - db_data) > 0.1:  # 소수점 오차 허용
                    mismatches.append({
                        'name': name,
                        'description': description,
                        'description_data': desc_data,
                        'db_data': db_data,
                        'difference': abs(desc_data - db_data)
                    })
    
    return mismatches

if __name__ == "__main__":
    print("🔍 데이터 용량 불일치 요금제 검사 시작...")
    
    mismatches = check_data_mismatches()
    
    if mismatches:
        print(f"\n❌ 데이터 불일치 발견: {len(mismatches)}개 요금제")
        print("=" * 100)
        
        for i, mismatch in enumerate(mismatches, 1):
            print(f"\n{i}. {mismatch['name']}")
            print(f"   📝 상품설명: {mismatch['description'][:100]}...")
            print(f"   📊 설명에서 추출된 데이터: {mismatch['description_data']}GB")
            print(f"   💾 DB에 저장된 데이터: {mismatch['db_data']}GB")
            print(f"   ⚠️  차이: {mismatch['difference']}GB")
            print("-" * 80)
    else:
        print("\n✅ 모든 요금제의 데이터 용량이 일치합니다!")
    
    driver.close()
    print(f"\n✅ 검사 완료!")