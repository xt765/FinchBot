# 部署指南

本文档介绍 FinchBot 的部署方式，包括本地部署、Docker 部署和生产环境建议。

## 目录

1. [本地部署](#1-本地部署)
2. [Docker 部署](#2-docker-部署)
3. [生产环境建议](#3-生产环境建议)
4. [安全性考虑](#4-安全性考虑)

---

## 1. 本地部署

### 前置要求

| 要求 | 说明 |
| :--- | :--- |
| 操作系统 | Windows / Linux / macOS |
| Python | 3.13+ |
| 包管理器 | uv (推荐) |
| 磁盘空间 | ~500MB (含嵌入模型) |

### 快速部署

```bash
# 1. 克隆仓库
git clone https://gitee.com/xt765/finchbot.git
# 或 git clone https://github.com/xt765/finchbot.git

cd finchbot

# 2. 安装依赖
uv sync

# 3. 配置
uv run finchbot config

# 4. 运行
uv run finchbot chat
```

---

## 2. Docker 部署

FinchBot 提供完整的 Docker 支持，支持一键部署。

### 快速开始

```bash
# 1. 克隆仓库
git clone https://gitee.com/xt765/finchbot.git
cd finchbot

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 3. 构建并启动
docker-compose up -d

# 4. 访问服务
# Web 界面: http://localhost:8000
# 健康检查: http://localhost:8000/health
```

### Dockerfile

项目根目录已包含生产级 `Dockerfile`：

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 包管理器
RUN pip install --no-cache-dir uv

# 复制项目文件
COPY pyproject.toml uv.toml README.md ./
COPY src/ ./src/

# 创建虚拟环境并安装依赖
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
RUN uv pip install --no-cache -e .

# 构建前端
COPY web/ ./web/
RUN cd web && npm ci && npm run build

# 配置环境
ENV STATIC_DIR=/app/web/dist
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "finchbot.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

项目根目录已包含 `docker-compose.yml`：

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

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker logs -f finchbot

# 停止服务
docker-compose down

# 重新构建
docker-compose up -d --build

# 进入容器调试
docker exec -it finchbot /bin/bash
```

### 环境变量配置

| 变量名 | 说明 | 必填 |
| :----- | :--- | :--: |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 二选一 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | 二选一 |
| `GOOGLE_API_KEY` | Google Gemini API 密钥 | 否 |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 否 |
| `TAVILY_API_KEY` | Tavily 搜索 API 密钥 | 否 |
| `FINCHBOT_LANGUAGE` | 界面语言 (zh-CN/en-US) | 否 |
| `FINCHBOT_DEFAULT_MODEL` | 默认模型名称 | 否 |

### 持久化存储

Docker Compose 配置了两个持久化卷：

| 卷名 | 路径 | 说明 |
| :--- | :--- | :--- |
| `finchbot_workspace` | `/root/.finchbot/workspace` | 会话数据、配置文件 |
| `finchbot_models` | `/root/.cache/huggingface` | 嵌入模型缓存 |

### 镜像加速（国内用户）

如果拉取基础镜像较慢，可配置 Docker 镜像加速器：

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

## 3. 生产环境建议

### 架构建议

```mermaid
flowchart TB
    classDef userLayer fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef appLayer fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef dataLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    subgraph Users [用户层]
        U[用户]:::userLayer
    end

    subgraph App [应用层]
        LB[负载均衡]:::appLayer
        API[API Server<br/>FastAPI]:::appLayer
        Agent[Agent<br/>LangGraph]:::appLayer
    end

    subgraph Data [数据层]
        PG[(PostgreSQL<br/>Checkpointer)]:::dataLayer
        Vector[(Vector DB<br/>Pinecone/Milvus)]:::dataLayer
        Redis[(Redis<br/>Cache)]:::dataLayer
    end

    U --> LB
    LB --> API
    API --> Agent
    Agent --> PG & Vector & Redis
```

### 数据库升级

| 组件 | 开发环境 | 生产环境 |
| :--- | :--- | :--- |
| Checkpointer | SQLite | PostgreSQL |
| 向量数据库 | ChromaDB (本地) | Pinecone / Milvus |
| 缓存 | 无 | Redis |

### 日志管理

```python
# 配置日志输出到 ELK Stack
import logging
from loguru import logger

# 移除默认处理器
logger.remove()

# 添加 JSON 格式输出
logger.add(
    "logs/finchbot.json",
    format="{message}",
    serialize=True,
    rotation="100 MB",
    retention="7 days"
)
```

### 监控指标

| 指标 | 说明 |
| :--- | :--- |
| 响应时间 | API 请求延迟 |
| Token 使用量 | LLM 调用统计 |
| 记忆存储量 | SQLite / Vector DB 大小 |
| 工具调用频率 | 各工具使用统计 |

---

## 4. 安全性考虑

### API Key 管理

```mermaid
flowchart LR
    classDef secure fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef insecure fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;

    A[API Key 存储]:::secure
    B[环境变量]:::secure
    C[密钥管理服务]:::secure
    D[硬编码]:::insecure
    E[配置文件]:::insecure

    A --> B
    A --> C
```

| 方式 | 安全性 | 推荐场景 |
| :--- | :---: | :--- |
| 环境变量 | ✅ 高 | 所有环境 |
| 密钥管理服务 | ✅ 高 | 生产环境 |
| 配置文件 | ⚠️ 中 | 开发环境 |
| 硬编码 | ❌ 低 | 不推荐 |

### Shell 执行安全

`ExecTool` 具有潜在风险，建议：

1. **黑名单过滤**: 默认禁用高危命令 (`rm -rf /`, `mkfs`, `dd`)
2. **沙箱隔离**: 在 Docker 容器中运行
3. **权限限制**: 使用非 root 用户运行
4. **超时控制**: 设置命令执行超时

```python
# 配置 Shell 执行限制
tools:
  exec:
    timeout: 60
    disabled_commands:
      - "rm -rf /"
      - "mkfs"
      - "dd"
      - "shutdown"
```

### 文件系统安全

```python
# 限制文件操作范围
tools:
  restrict_to_workspace: true
```

| 设置 | 说明 |
| :--- | :--- |
| `restrict_to_workspace: true` | 文件操作限制在工作区内 |
| `restrict_to_workspace: false` | 允许访问任意路径（不推荐） |

---

## 部署检查清单

- [ ] API Key 已配置为环境变量
- [ ] 文件操作限制在工作区
- [ ] Shell 执行已配置黑名单
- [ ] 日志输出已配置
- [ ] 数据库备份策略已设置
- [ ] 监控告警已配置
