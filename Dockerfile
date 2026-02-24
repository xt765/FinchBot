FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /root/.finchbot/workspace

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.toml README.md ./
COPY src/ ./src/

RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"
ENV PYTHONPATH="/app/src"

RUN uv pip install --no-cache -e .

COPY web/package*.json ./web/

WORKDIR /app/web
RUN npm ci

WORKDIR /app
COPY web/ ./web/
RUN cd web && npm run build

COPY langgraph.json ./

ENV FINCHBOT_WORKSPACE=/root/.finchbot/workspace
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV STATIC_DIR=/app/web/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "finchbot.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
