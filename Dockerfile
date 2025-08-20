FROM python:3.12.9-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libpq-dev \
    python3-dev \
    build-essential

RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=2.1.1 POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml .
COPY poetry.lock .


RUN poetry --version
RUN poetry install --only main --no-root
COPY . .

EXPOSE 80

ARG VERSION="1.0.0"
ENV DD_VERSION=$VERSION
ENV APP_VERSION=$VERSION

ARG STACK_TYPE="local"
ENV STACK_TYPE=$STACK_TYPE

COPY ./entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENTRYPOINT [ "./entrypoint.sh" ]
