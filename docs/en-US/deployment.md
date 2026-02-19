# Deployment Guide

## Local Deployment

### 1. Using Docker

FinchBot does not yet provide an official Docker image, but you can build one using the following `Dockerfile`:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY README.md ./

# Install dependencies
RUN uv sync --frozen

# Set entrypoint
ENTRYPOINT ["uv", "run", "finchbot"]
CMD ["chat"]
```

Build and run:

```bash
docker build -t finchbot .
docker run -it -v ~/.finchbot:/root/.finchbot finchbot chat
```

## Production Environment Recommendations

- **Database**: For production, it is recommended to replace SQLite with PostgresSQL (LangGraph Checkpointer).
- **Vector Database**: Local ChromaDB is suitable for single-node deployment; for larger scale, consider using remote vector databases (like Pinecone or Milvus).
- **Logging**: Recommended to redirect logs to a centralized logging system (like ELK Stack).

## Security

- **API Key**: Ensure keys are stored in environment variables, never hardcoded in code or configuration files.
- **Shell Execution**: `ExecTool` has potential risks; blacklist filtering is enabled by default. For production, running in a sandbox (Docker/Firecracker) is recommended.
