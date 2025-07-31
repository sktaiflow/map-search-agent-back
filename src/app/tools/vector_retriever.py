import asyncio
import logging
import os
from typing import Dict, List, Optional

import asyncpg
import numpy as np
from openai import OpenAI
import ollama

logger = logging.getLogger(__name__)

class FewShotRetriever:
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE", "https://aihub-api.sktelecom.com/aihub/v2/sandbox")
        )
        self.db_config = {
            'host': os.getenv("PGVECTOR_HOST", "localhost"),
            'port': int(os.getenv("PGVECTOR_PORT", 5432)),
            'database': os.getenv("PGVECTOR_DBNAME", "vectordb"),
            'user': os.getenv("PGVECTOR_USER", "postgres"),
            'password': os.getenv("PGVECTOR_PASSWORD")
        }
    
    async def get_embedding(self, text: str) -> List[float]:
        """텍스트의 임베딩 벡터 생성"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            return None
    
    async def find_similar_examples(
        self, 
        query: str, 
        top_k: int = 3,
        min_similarity: float = 0.5
    ) -> List[Dict]:
        """유사한 Few-shot 예시 검색"""
        
        # 1. 쿼리 임베딩 생성
        query_embedding = await self.get_embedding(query)
        if not query_embedding:
            logger.warning(f"임베딩 생성 실패: {query}")
            return []
        
        # 2. 벡터 유사도 검색
        conn = await asyncpg.connect(**self.db_config)
        try:
            # PostgreSQL vector 형식으로 변환
            vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            sql = """
                SELECT 
                    natural_language,
                    cypher_query,
                    quality_score,
                    domain_tags,
                    1 - (nl_embedding <=> $1::vector) AS similarity
                FROM few_shot_examples 
                WHERE 1 - (nl_embedding <=> $1::vector) >= $2
                ORDER BY nl_embedding <=> $1::vector
                LIMIT $3
            """
            
            rows = await conn.fetch(sql, vector_str, min_similarity, top_k)
            
            # 3. 결과 처리
            examples = []
            for row in rows:
                examples.append({
                    'natural_language': row['natural_language'],
                    'cypher_query': row['cypher_query'],
                    'similarity': float(row['similarity']),
                    'quality_score': float(row['quality_score']),
                    'domain_tags': row['domain_tags']
                })
            
            logger.info(f"벡터 검색 결과: {len(examples)}개 (유사도 >= {min_similarity})")
            return examples
            
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return []
        finally:
            await conn.close()
    
    async def _update_usage_stats(self, conn, used_examples: List[str]):
        """사용 통계 업데이트"""
        try:
            await conn.execute("""
                UPDATE few_shot_examples 
                SET usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE natural_language = ANY($1::text[])
            """, used_examples)
        except Exception as e:
            logger.warning(f"사용 통계 업데이트 실패: {e}")



class FewShotRetrieverOllama:
    """Ollama 기반 FewShotRetriever"""
    def __init__(self):
        # Ollama 임베딩 모델 설정 (환경변수 OLLAMA_EMBED_MODEL, 기본 nomic-embed-text)
        self.emb_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.client = ollama.Client(host="http://host.docker.internal:11434")
        # 벡터 DB 설정은 기존과 동일
        self.db_config = {
            'host': os.getenv("PGVECTOR_HOST", "localhost"),
            'port': int(os.getenv("PGVECTOR_PORT", 5432)),
            'database': os.getenv("PGVECTOR_DBNAME", "vectordb"),
            'user': os.getenv("PGVECTOR_USER", "postgres"),
            'password': os.getenv("PGVECTOR_PASSWORD")
        }

    async def get_embedding(self, text: str) -> List[float]:
        """텍스트의 임베딩 벡터 생성 via Ollama"""
        try:
            # ollama.embed은 블로킹 호출이므로 스레드에서 실행
            response = await asyncio.to_thread(
                self.client.embed,
                model=self.emb_model,
                input=text
            )
            embed_vec = response.get("embeddings")[0]
            if len(embed_vec) != 1536:
                embed_vec = embed_vec + [0.0] * (1536 - len(embed_vec))
                
            return embed_vec
        except Exception as e:
            logger.error(f"임베딩 생성 실패 (Ollama): {e}")
            return None

    async def find_similar_examples(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.5
    ) -> List[Dict]:
        """유사한 Few-shot 예시 검색 (Ollama)"""
        # 나머지 로직은 FewShotRetriever.find_similar_examples 그대로 복사
        return await FewShotRetriever.find_similar_examples(self, query, top_k, min_similarity)

    async def _update_usage_stats(self, conn, used_examples: List[str]):
        """사용 통계 업데이트 (Ollama)"""
        # 나머지 로직은 FewShotRetriever._update_usage_stats 그대로 복사
        return await FewShotRetriever._update_usage_stats(self, conn, used_examples)


# 전역 인스턴스
few_shot_retriever = FewShotRetriever()
# few_shot_retriever = FewShotRetrieverOllama()