# 部署指南

## 本地部署

### 1. 使用 Docker

FinchBot 尚未提供官方 Docker 镜像，但可以通过以下 `Dockerfile` 构建：

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY README.md ./

# 安装依赖
RUN uv sync --frozen

# 设置入口点
ENTRYPOINT ["uv", "run", "finchbot"]
CMD ["chat"]
```

构建并运行：

```bash
docker build -t finchbot .
docker run -it -v ~/.finchbot:/root/.finchbot finchbot chat
```

### 2. 使用 Systemd (Linux)

可以作为后台服务运行（如果实现了 WebSocket Server 模式）。目前 FinchBot 主要是 CLI 应用，更适合作为交互式工具使用。

## 生产环境建议

- **数据库**: 生产环境建议将 SQLite 替换为 PostgresSQL (LangGraph Checkpointer)。
- **向量数据库**: 本地 ChromaDB 适合单机部署，大规模部署建议使用远程向量数据库 (如 Pinecone 或 Milvus)。
- **日志**: 建议将日志输出重定向到 centralized logging system (如 ELK Stack)。

## 安全性

- **API Key**: 确保存储在环境变量中，不要硬编码在代码或配置文件中。
- **Shell 执行**: `ExecTool` 具有潜在风险，默认启用黑名单过滤，生产环境建议在沙箱 (Docker/Firecracker) 中运行。
