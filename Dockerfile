FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Create .env.local if it doesn't exist
RUN if [ ! -f .env.local ]; then \
    echo "STACK_TYPE=local" > .env.local && \
    echo "APP_NAME=map-search-agent-back" >> .env.local && \
    echo "API_VERSION=0.1.0" >> .env.local && \
    echo "OPENAI_API_BASE=https://api.openai.com/v1" >> .env.local && \
    echo "OPENAI_API_KEY=dummy-key-for-test" >> .env.local && \
    echo "AWS_REGION=ap-northeast-2" >> .env.local && \
    echo "NEO4J_NLB_DNS=localhost" >> .env.local && \
    echo "NLB_PORT=7687" >> .env.local && \
    echo "NEO4J_USERNAME=neo4j" >> .env.local && \
    echo "NEO4J_PASSWORD=password" >> .env.local; \
    fi

EXPOSE 8002

CMD ["uv", "run", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8002"]