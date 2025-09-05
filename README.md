# map-search-agent-back
map-search-agent backend code

# local 실행 명령어
STACK_TYPE=local uv run --frozen uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload