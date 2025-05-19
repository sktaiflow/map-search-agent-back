# map-search-agent
map-search-agent repository in "데이터 모델링팀"

## Neo4j 연결 설정
Neo4j 연결 URL은 실행 환경에 따라 다르게 설정해야 합니다:
- LangGraph 환경: `url="bolt://localhost:7687"`
- OpenWebUI 환경: `url="bolt://neo4j-gds-apoc-n10s:7687"`

## Local 개발 환경 설정

### 1. LangGraph 실행
```bash
# LangGraph 서버 실행
langgraph serve
```

### 2. Neo4j 컨테이너 실행
```bash
# Docker Compose로 Neo4j 컨테이너 실행
docker compose up -d
```

### 주의사항
- LangGraph 환경에서는 Neo4j 연결 URL을 `bolt://localhost:7687`로 설정합니다.
- OpenWebUI 환경에서는 `bolt://neo4j-gds-apoc-n10s:7687`를 사용합니다.
- Neo4j 컨테이너가 실행되면 기본 접속 정보는 다음과 같습니다:
  - Username: neo4j
  - Password: neo4jpassword
  - Port: 7687