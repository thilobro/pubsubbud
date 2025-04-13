FROM python:3.11-slim AS build

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir poetry
RUN poetry add duckdb
RUN poetry install
WORKDIR /app/examples/cli_chat

CMD ["poetry", "run", "python", "cli_chat_server.py"]
