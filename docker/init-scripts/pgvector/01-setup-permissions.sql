-- PostgreSQL 초기화 스크립트: 사용자 권한 설정
-- 이 스크립트는 컨테이너 시작시 자동으로 실행됩니다

\echo '=== Starting PostgreSQL permissions setup ==='

-- pguser 사용자가 없으면 생성
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'pguser') THEN
        CREATE USER pguser WITH PASSWORD 'postgrespassword';
        \echo 'Created user: pguser';
    ELSE
        \echo 'User pguser already exists';
    END IF;
END $$;

-- pguser에게 데이터베이스 연결 권한 부여
GRANT CONNECT ON DATABASE vectordb TO pguser;
\echo 'Granted CONNECT privilege on vectordb to pguser';

-- pguser에게 public 스키마 사용 권한 부여
GRANT USAGE ON SCHEMA public TO pguser;
GRANT CREATE ON SCHEMA public TO pguser;
\echo 'Granted USAGE and CREATE privileges on public schema to pguser';

-- 모든 기존 테이블에 대한 권한 부여
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pguser;
\echo 'Granted table privileges on existing tables to pguser';

-- 모든 기존 시퀀스에 대한 권한 부여
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pguser;
\echo 'Granted sequence privileges on existing sequences to pguser';

-- 향후 생성될 테이블과 시퀀스에 대한 기본 권한 설정
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pguser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO pguser;
\echo 'Set default privileges for future tables and sequences';

-- pgvector 확장 활성화 (이미 있으면 무시)
CREATE EXTENSION IF NOT EXISTS vector;
\echo 'Ensured vector extension is available';

\echo '=== PostgreSQL permissions setup completed ==='