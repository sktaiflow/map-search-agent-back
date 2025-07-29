import asyncio
import json
import os
import time
from typing import List

import asyncpg
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

env_path = "docker/.env"
load_dotenv(env_path)

class FewShotDataInserter:
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE", "https://aihub-api.sktelecom.com/aihub/v2/sandbox")
        )
        self.db_config = {
            'host': "localhost",
            'port': int(os.getenv("PGVECTOR_PORT", 5432)),
            'database': os.getenv("PGVECTOR_DBNAME", "vectordb"),
            'user': os.getenv("PGVECTOR_USER", "pguser"),
            'password': os.getenv("PGVECTOR_PASSWORD")
        }
    
    async def get_embedding(self, text: str) -> List[float]:
        """OpenAI 임베딩 생성"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"임베딩 생성 실패 for '{text[:30]}...': {e}")
            return None
    
    async def insert_data(self, csv_file: str = None):
        """CSV 데이터를 데이터베이스에 삽입"""
        
        # ✅ CSV 파일 경로 자동 설정
        if csv_file is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_file = os.path.join(script_dir, 'few_shot_data.csv')
        
        # ✅ 파일 존재 확인
        if not os.path.exists(csv_file):
            print(f"❌ CSV 파일을 찾을 수 없습니다: {csv_file}")
            return
        
        print(f"📁 CSV 파일 경로: {csv_file}")
        df = pd.read_csv(csv_file)
        
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            print(f"📁 CSV 파일 로드: {len(df)}개 레코드")
            
            success_count = 0
            for idx, row in df.iterrows():
                print(f"처리 중: {idx+1}/{len(df)} - {row['natural_language'][:50]}...")
                
                # 임베딩 생성
                embedding = await self.get_embedding(row['natural_language'])
                if embedding is None:
                    print(f"⚠️  임베딩 생성 실패로 건너뜀: {row['natural_language'][:30]}...")
                    continue
                
                # domain_tags 파싱 (문자열로 저장된 리스트를 파싱)
                try:
                    domain_tags = eval(row['domain_tags']) if isinstance(row['domain_tags'], str) else row['domain_tags']
                except:
                    domain_tags = []
                
                # 데이터베이스 삽입
                try:
                    # ✅ 임베딩을 PostgreSQL vector 형식으로 변환
                    if isinstance(embedding, list):
                        vector_str = '[' + ','.join(map(str, embedding)) + ']'
                    else:
                        vector_str = str(embedding)
                    
                    await conn.execute("""
                        INSERT INTO few_shot_examples (
                            natural_language, 
                            cypher_query, 
                            nl_embedding,
                            domain_tags,
                            quality_score
                        ) VALUES ($1, $2, $3, $4, $5)
                    """, 
                    row['natural_language'],
                    row['cypher_query'],
                    vector_str,
                    domain_tags,
                    float(row['quality_score'])
                    )
                    
                    success_count += 1
                    print(f"✅ 성공: {idx+1}/{len(df)}")
                    
                    # API 레이트 리밋 고려
                    if idx % 5 == 0:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    print(f"💥 처리 중 오류 발생! 전체 프로세스를 중단합니다.")
                    print(f"❌ 오류 내용: {e}")
                    print(f"📊 처리 완료된 레코드: {success_count}/{idx+1}")
                    # ✅ 예외를 다시 발생시켜 전체 함수 종료
                    raise e
                    
            print(f"🎉 데이터 삽입 완료! 성공: {success_count}/{len(df)}")
            
            # 삽입된 데이터 확인
            count = await conn.fetchval("SELECT COUNT(*) FROM few_shot_examples")
            print(f"📊 총 레코드 수: {count}")
            
        finally:
            await conn.close()

async def main():
    inserter = FewShotDataInserter()
    
    await inserter.insert_data()

if __name__ == "__main__":
    asyncio.run(main())