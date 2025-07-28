-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- Few-shot 예시 테이블
CREATE TABLE IF NOT EXISTS few_shot_examples (
    id SERIAL PRIMARY KEY,
    
    -- 핵심 데이터
    natural_language TEXT NOT NULL,
    cypher_query TEXT NOT NULL,
    nl_embedding vector(1536),
    
    -- 운영 지표
    quality_score FLOAT DEFAULT 1.0,
    usage_count INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    
    -- 메타데이터
    domain_tags TEXT[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 벡터 유사도 검색 인덱스
CREATE INDEX few_shot_nl_embedding_idx 
ON few_shot_examples USING ivfflat (nl_embedding vector_cosine_ops) 
WITH (lists = 100);

-- 성능 최적화 인덱스
CREATE INDEX few_shot_quality_idx ON few_shot_examples(quality_score DESC, is_active);
CREATE INDEX few_shot_usage_idx ON few_shot_examples(usage_count DESC, success_rate DESC);
CREATE INDEX few_shot_domain_tags_idx ON few_shot_examples USING GIN(domain_tags);

-- 성능 로그 테이블
CREATE TABLE IF NOT EXISTS few_shot_performance_log (
    id SERIAL PRIMARY KEY,
    user_query TEXT NOT NULL,
    used_examples TEXT[] NOT NULL,
    generated_cypher TEXT,
    execution_success BOOLEAN NOT NULL,
    execution_error TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 성능 분석용 인덱스
CREATE INDEX few_shot_perf_success_idx ON few_shot_performance_log(execution_success, created_at);
CREATE INDEX few_shot_perf_examples_idx ON few_shot_performance_log USING GIN(used_examples);

-- 업데이트 시간 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_few_shot_updated_at 
    BEFORE UPDATE ON few_shot_examples 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 초기화 완료 확인
DO $$
BEGIN
    RAISE NOTICE 'Few-shot database schema initialized successfully!';
END $$;