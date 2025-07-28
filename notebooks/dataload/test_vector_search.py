# notebooks/dataload/simple_vector_test.py

import asyncio
import os
from typing import Dict, List

import asyncpg
from dotenv import load_dotenv
from openai import OpenAI

# 환경변수 로드
env_path = "/Users/hazel/Documents/map-search-agent/docker/.env"
load_dotenv(env_path)

class SimpleVectorRetriever:
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE", "https://aihub-api.sktelecom.com/aihub/v2/sandbox")
        )
        self.db_config = {
            'host': "localhost",
            'port': int(os.getenv("PGVECTOR_PORT", 5432)),
            'database': os.getenv("PGVECTOR_DBNAME", "vectordb"),
            'user': os.getenv("PGVECTOR_USER", "postgres"),
            'password': os.getenv("PGVECTOR_PASSWORD")
        }
    
    async def get_embedding(self, text: str) -> List[float]:
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"임베딩 생성 실패: {e}")
            return None
    
    async def find_similar_examples(self, query: str, top_k: int = 3, min_similarity: float = 0.0):
        print(f"🔍 검색: '{query}' (최소 유사도: {min_similarity})")
        
        # 쿼리 임베딩 생성
        query_embedding = await self.get_embedding(query)
        if not query_embedding:
            return []
        
        print(f"✅ 임베딩 생성 완료, 차원: {len(query_embedding)}")
        
        # 데이터베이스 검색
        conn = await asyncpg.connect(**self.db_config)
        try:
            vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # ✅ 유사도 조건을 WHERE절에 추가
            sql = """
            SELECT 
                natural_language,
                cypher_query,
                quality_score,
                domain_tags,
                1 - (nl_embedding <=> $1::vector) AS similarity
            FROM few_shot_examples 
            WHERE 1 - (nl_embedding <=> $1::vector) >= $3
            ORDER BY nl_embedding <=> $1::vector
            LIMIT $2
            """
            
            rows = await conn.fetch(sql, vector_str, top_k, min_similarity)
            
            print(f"📊 검색 결과: {len(rows)}개 (유사도 >= {min_similarity})")
            for i, row in enumerate(rows, 1):
                print(f"  {i}. 유사도: {row['similarity']:.3f}")
                print(f"     질문: {row['natural_language']}")
                print(f"     쿼리: {row['cypher_query'][:60]}...")
                print()
            
            return rows
            
        except Exception as e:
            print(f"❌ 검색 중 오류 발생: {e}")
            return []
            
        finally:
            await conn.close()

async def test():
    retriever = SimpleVectorRetriever()
    
    test_queries = [
        "18세 미만만 가입할 수 있는 요금제가 있어?",
        "데이터 많이 쓰는 요금제 추천해줘",
        "VIP 멤버십 되는 요금제"
    ]
    
    for query in test_queries:
        print("="*60)
        # ✅ 양수 유사도만 허용
        await retriever.find_similar_examples(query, top_k=5, min_similarity=0.0)

if __name__ == "__main__":
    asyncio.run(test())