FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings (dev dendency는 제외)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PYTHONPATH="/app"
ENV PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libpq-dev \
    python3-dev \
    build-essential


EXPOSE 80
EXPOSE 8000

ARG VERSION="1.0.0"
ENV APP_VERSION=$VERSION

ARG STACK_TYPE="local"
ENV STACK_TYPE=$STACK_TYPE

#COPY ./entrypoint.sh ./entrypoint.sh
#RUN chmod +x ./entrypoint.sh

CMD ["uv", "run", "--frozen", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]