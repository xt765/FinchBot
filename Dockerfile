FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /root/.finchbot/workspace

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.toml ./

RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

RUN uv pip install --no-cache -e .

COPY web/package*.json ./web/

WORKDIR /app/web
RUN npm ci

WORKDIR /app
COPY web/ ./web/
RUN cd web && npm run build

COPY src/ ./src/
COPY langgraph.json ./

ENV FINCHBOT_WORKSPACE=/root/.finchbot/workspace
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV STATIC_DIR=/app/web/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "finchbot.server.main"]
