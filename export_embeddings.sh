#!/bin/bash

# pgvector 테이블 덤프 스크립트
# 실행 중인 도커 컨테이너에 전혀 영향 없음 (읽기 전용)

echo "🔍 pgvector 컨테이너 상태 확인..."
docker ps | grep pgvector-container

echo "📦 few_shot_examples 테이블 덤프 시작..."

# 환경변수 로드 (실제 컨테이너 설정에 맞춤)
PGVECTOR_HOST=${PGVECTOR_HOST:-localhost}
PGVECTOR_PORT=${PGVECTOR_PORT:-5432}
PGVECTOR_USER=${PGVECTOR_USER:-pguser}
PGVECTOR_DBNAME=${PGVECTOR_DBNAME:-vectordb}
PGVECTOR_PASSWORD=${PGVECTOR_PASSWORD:-postgrespassword}

# 패스워드를 환경변수로 설정
export PGPASSWORD=$PGVECTOR_PASSWORD

# 테이블만 선택적으로 덤프 (안전한 옵션들만 사용)
pg_dump \
  -h $PGVECTOR_HOST \
  -p $PGVECTOR_PORT \
  -U $PGVECTOR_USER \
  -d $PGVECTOR_DBNAME \
  --table=few_shot_examples \
  --data-only \
  --no-owner \
  --no-privileges \
  --inserts \
  --verbose \
  > few_shot_embeddings.sql

echo "✅ 덤프 완료!"
echo "📁 파일 크기: $(ls -lh few_shot_embeddings.sql | awk '{print $5}')"
echo "📊 행 수: $(grep -c "INSERT INTO" few_shot_embeddings.sql)"

echo ""
echo "🚀 동료에게 전달할 파일: few_shot_embeddings.sql"
echo "💡 이 파일을 AWS RDS에서 다음 명령으로 import 가능:"
echo "   psql -h your-rds-host -U postgres -d vectordb -f few_shot_embeddings.sql"