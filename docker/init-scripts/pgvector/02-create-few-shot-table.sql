-- Few-shot examples 테이블 생성 스크립트
-- 테이블이 없으면 생성하고, 있으면 권한만 재설정

\echo '=== Setting up few_shot_examples table ==='

-- few_shot_examples 테이블 생성 (이미 있으면 무시)
CREATE TABLE IF NOT EXISTS few_shot_examples (
    id SERIAL PRIMARY KEY,
    natural_language TEXT NOT NULL,
    cypher_query TEXT NOT NULL,
    quality_score FLOAT DEFAULT 0.0,
    domain_tags TEXT[],
    nl_embedding vector(1536),  -- OpenAI text-embedding-3-small 차원
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(natural_language)
);

\echo 'few_shot_examples table created or already exists';

-- 인덱스 생성 (이미 있으면 무시)
CREATE INDEX IF NOT EXISTS idx_few_shot_embedding ON few_shot_examples USING ivfflat (nl_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_few_shot_quality ON few_shot_examples (quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_few_shot_usage ON few_shot_examples (usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_few_shot_created ON few_shot_examples (created_at DESC);

\echo 'Indexes created or already exist';

-- pguser에게 명시적으로 테이블 권한 부여
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE few_shot_examples TO pguser;
GRANT USAGE, SELECT ON SEQUENCE few_shot_examples_id_seq TO pguser;

\echo 'Granted permissions on few_shot_examples table to pguser';

-- 샘플 데이터 삽입 (중복 방지)
INSERT INTO few_shot_examples (natural_language, cypher_query, quality_score, domain_tags) 
VALUES 
    ('데이터 30기가면 될 것 같은데 내가 가입가능한 요금제가 뭐가 있을까?', 
     'MATCH (p:`요금제`)-[:`제공`]->(d:`데이터용량`) WHERE d.`기본제공데이터용량` >= 30 RETURN p, d',
     0.9, 
     ARRAY['데이터용량', '요금제검색'])
ON CONFLICT (natural_language) DO NOTHING;

INSERT INTO few_shot_examples (natural_language, cypher_query, quality_score, domain_tags) 
VALUES 
    ('만 25세인데 가입할 수 있는 요금제는?', 
     'MATCH (p:`요금제`) WHERE p.`가입가능최소나이` <= 25 AND p.`가입가능최대나이` >= 25 RETURN p',
     0.8, 
     ARRAY['연령제한', '요금제검색'])
ON CONFLICT (natural_language) DO NOTHING;

\echo 'Sample data inserted (if not already present)';

-- 테이블 상태 확인
\echo '=== Table information ==='
\d few_shot_examples

-- 권한 확인
\echo '=== Permission check ==='
\dp few_shot_examples

\echo '=== few_shot_examples setup completed ==='