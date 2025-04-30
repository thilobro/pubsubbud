FROM python:3.11-slim AS build

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir poetry
RUN poetry install

WORKDIR /app/examples/test_server

CMD ["poetry", "run", "python", "test_server.py"] 