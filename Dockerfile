# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

# Descobre e instala automaticamente as bibliotecas de instrumentação OTel
# compatíveis com o que está instalado (Flask, requests, psycopg2 etc.).
RUN opentelemetry-bootstrap -a install

EXPOSE 8002

# Sem --preload: cada worker gunicorn importa app.py após o fork, então o
# exporter OTLP/HTTP (configurado via OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
# no Deployment) não herda conexões/threads pré-fork problemáticas, como
# ocorreria com o transporte gRPC.
CMD ["opentelemetry-instrument", "gunicorn", "--bind", "0.0.0.0:8002", "app:app"]
