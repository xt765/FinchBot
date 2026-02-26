FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
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

ENV FINCHBOT_WORKSPACE=/root/.finchbot/workspace
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["finchbot", "chat"]
