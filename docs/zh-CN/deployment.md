# 

 FinchBot Docker 

## 

1. [](#1-)
2. [Docker ](#2-docker-)
3. [](#3-)
4. [](#4-)

---

## 1. 

### 

|  |  |
| :--- | :--- |
|  | Windows / Linux / macOS |
| Python | 3.13+ |
|  | uv () |
|  | ~500MB () |

### 

```bash
# 1. 
git clone https://gitee.com/xt765/finchbot.git
#  git clone https://github.com/xt765/finchbot.git

cd finchbot

# 2. 
uv sync

# 3. 
uv run finchbot config

# 4. 
uv run finchbot chat
```

---

## 2. Docker 

FinchBot  Docker 

### 

```bash
# 1. 
git clone https://gitee.com/xt765/finchbot.git
cd finchbot

# 2. 
cp .env.example .env
#  .env  API Key

# 3. 
docker-compose up -d

# 4. 
# Web : http://localhost:8000
# : http://localhost:8000/health
```

### Dockerfile

 `Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*

#  Python 
RUN pip install --no-cache-dir uv

# 
COPY pyproject.toml uv.toml README.md ./
COPY src/ ./src/

# 
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
RUN uv pip install --no-cache -e .

# 
COPY web/ ./web/
RUN cd web && npm ci && npm run build

# 
ENV STATIC_DIR=/app/web/dist
EXPOSE 8000

# 
CMD ["uvicorn", "finchbot.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

 `docker-compose.yml`

```yaml
services:
  finchbot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: finchbot
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - FINCHBOT_LANGUAGE=${FINCHBOT_LANGUAGE:-zh-CN}
    volumes:
      - finchbot_workspace:/root/.finchbot/workspace
      - finchbot_models:/root/.cache/huggingface
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  finchbot_workspace:
  finchbot_models:
```

### 

```bash
# 
docker-compose up -d

# 
docker logs -f finchbot

# 
docker-compose down

# 
docker-compose up -d --build

# 
docker exec -it finchbot /bin/bash
```

### 

|  |  |  |
| :----- | :--- | :--: |
| `OPENAI_API_KEY` | OpenAI API  |  |
| `ANTHROPIC_API_KEY` | Anthropic API  |  |
| `GOOGLE_API_KEY` | Google Gemini API  |  |
| `DEEPSEEK_API_KEY` | DeepSeek API  |  |
| `TAVILY_API_KEY` | Tavily  API  |  |
| `FINCHBOT_LANGUAGE` |  (zh-CN/en-US) |  |
| `FINCHBOT_DEFAULT_MODEL` |  |  |

### 

Docker Compose 

|  |  |  |
| :--- | :--- | :--- |
| `finchbot_workspace` | `/root/.finchbot/workspace` |  |
| `finchbot_models` | `/root/.cache/huggingface` |  |

### 

 Docker 

```json
// Docker Desktop -> Settings -> Docker Engine
{
  "registry-mirrors": [
    "https://dockerhub.icu",
    "https://hub.rat.dev"
  ]
}
```

---

## 3. 

### 

```mermaid
flowchart TB
    classDef userLayer fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef appLayer fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef dataLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    subgraph Users []
        U[]:::userLayer
    end

    subgraph App []
        LB[]:::appLayer
        API[API Server<br/>FastAPI]:::appLayer
        Agent[Agent<br/>LangGraph]:::appLayer
    end

    subgraph Data []
        PG[(PostgreSQL<br/>Checkpointer)]:::dataLayer
        Vector[(Vector DB<br/>Pinecone/Milvus)]:::dataLayer
        Redis[(Redis<br/>Cache)]:::dataLayer
    end

    U --> LB
    LB --> API
    API --> Agent
    Agent --> PG & Vector & Redis
```

### 

|  |  |  |
| :--- | :--- | :--- |
| Checkpointer | SQLite | PostgreSQL |
|  | ChromaDB () | Pinecone / Milvus |
|  |  | Redis |

### 

```python
#  ELK Stack
import logging
from loguru import logger

# 
logger.remove()

#  JSON 
logger.add(
    "logs/finchbot.json",
    format="{message}",
    serialize=True,
    rotation="100 MB",
    retention="7 days"
)
```

### 

|  |  |
| :--- | :--- |
|  | API  |
| Token  | LLM  |
|  | SQLite / Vector DB  |
|  |  |

---

## 4. 

### API Key 

```mermaid
flowchart LR
    classDef secure fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef insecure fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;

    A[API Key ]:::secure
    B[]:::secure
    C[]:::secure
    D[]:::insecure
    E[]:::insecure

    A --> B
    A --> C
```

|  |  |  |
| :--- | :---: | :--- |
|  |   |  |
|  |   |  |
|  |   |  |
|  |   |  |

### Shell 

`ExecTool` 

1. ****:  (`rm -rf /`, `mkfs`, `dd`)
2. ****:  Docker 
3. ****:  root 
4. ****: 

```python
#  Shell 
tools:
  exec:
    timeout: 60
    disabled_commands:
      - "rm -rf /"
      - "mkfs"
      - "dd"
      - "shutdown"
```

### 

```python
# 
tools:
  restrict_to_workspace: true
```

|  |  |
| :--- | :--- |
| `restrict_to_workspace: true` |  |
| `restrict_to_workspace: false` |  |

---

## 

- [ ] API Key 
- [ ] 
- [ ] Shell 
- [ ] 
- [ ] 
- [ ] 
