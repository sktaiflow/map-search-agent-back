# Makefile 예시 (일부)
.PHONY: help test lint format docker-build infra-up

# 도움말 기본 타깃
help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?##"}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'
        
test: ## 단위 테스트 실행
	pytest -q

lint: ## 코드 스타일 검사
	ruff check .

format: ## Black으로 자동 포맷
	black .

docker-build: ## 도커 이미지 빌드
	docker build -t myapp:latest .

infra-up: ## 인프라(예: docker compose, terraform) 기동
	docker compose up -d