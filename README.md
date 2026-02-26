# FinchBot - A Lightweight, Flexible, and Infinitely Extensible AI Agent Framework

<p align="center">
  <img src="docs/image/image.png" alt="FinchBot Logo" width="600">
</p>

<p align="center">
  <em>Built on LangChain v1.2 and LangGraph v1.0<br>
  with persistent memory, dynamic prompts, and seamless tool integration</em>
</p>

<p align="center">
  <a href="https://blog.csdn.net/Yunyi_Chi">
    <img src="https://img.shields.io/badge/CSDN-玄同765-orange?style=flat-square&logo=csdn" alt="CSDN Blog">
  </a>
  <a href="https://github.com/xt765/FinchBot">
    <img src="https://img.shields.io/badge/GitHub-FinchBot-black?style=flat-square&logo=github" alt="GitHub">
  </a>
  <a href="https://gitee.com/xt765/FinchBot">
    <img src="https://img.shields.io/badge/Gitee-FinchBot-red?style=flat-square&logo=gitee" alt="Gitee">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Ruff-Formatter-orange?style=flat-square&logo=ruff" alt="Ruff">
  <img src="https://img.shields.io/badge/Basedpyright-TypeCheck-purple?style=flat-square&logo=python" alt="Basedpyright">
  <img src="https://img.shields.io/badge/Docker-Containerized-blue?style=flat-square&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square&logo=open-source-initiative" alt="License">
</p>

**FinchBot** is a lightweight, modular AI Agent framework built on **LangChain v1.2** and **LangGraph v1.0**. It is not just another LLM wrapper. It is a thoughtfully designed architecture focused on three core challenges:

1. **How to enable infinite Agent extensibility?** - Through a dual-layer extension mechanism of Skills and Tools
2. **How to give Agents real memory?** - Through a dual-layer storage architecture and Agentic RAG
3. **How to make Agent behavior customizable?** - Through a dynamic prompt file system

[中文文档](README_CN.md) | [English Documentation](docs/en-US/README.md)

## Table of Contents

1. [Why FinchBot?](#why-finchbot)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Quick Start](#quick-start)
5. [Tech Stack](#tech-stack)
6. [Extension Guide](#extension-guide)
7. [Documentation](#documentation)

---

## Why FinchBot?

### Pain Points of Existing Frameworks

| Pain Point | Traditional Approach | FinchBot Solution |
|------------|---------------------|-------------------|
| Hard to Extend | Requires modifying core code | Inherit base class or create Markdown files |
| Fragile Memory | Relies on LLM context window | Dual-layer persistent storage and semantic retrieval |
| Rigid Prompts | Hardcoded in source code | File system with hot reloading |
| Slow Startup | Synchronous blocking I/O | Fully async with Thread pool concurrency |
| Outdated Architecture | Based on old LangChain APIs | LangChain v1.2 and LangGraph v1.0 |

### Design Philosophy

```mermaid
graph BT
    classDef roof fill:#ffebee,stroke:#c62828,stroke-width:3px,color:#b71c1c,rx:10,ry:10;
    classDef pillar fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1,rx:8,ry:8;
    classDef base fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px,color:#1b5e20,rx:10,ry:10;

    Roof("FinchBot Framework<br/>Lightweight - Flexible - Extensible"):::roof

    subgraph Pillars [Core Philosophy]
        direction LR
        P("Privacy First<br/>Local Embedding<br/>No Cloud Upload"):::pillar
        M("Modularity<br/>Factory Pattern<br/>Decoupled Design"):::pillar
        D("Dev Friendly<br/>Type Safety<br/>Rich Documentation"):::pillar
        S("Fast Startup<br/>Fully Async<br/>Thread Pool"):::pillar
        O("Out of Box<br/>Zero Config<br/>Auto Fallback"):::pillar
    end

    Base("Tech Foundation<br/>LangChain v1.2 - LangGraph v1.0 - Python 3.13"):::base

    Base === P & M & D & S & O
    P & M & D & S & O === Roof
```

### Multi-Platform Messaging

FinchBot unified message routing architecture - develop once, reach everywhere:

![Web](https://img.shields.io/badge/Web-WebSocket-blue?logo=googlechrome&logoColor=white) ![Discord](https://img.shields.io/badge/Discord-Bot_API-5865F2?logo=discord&logoColor=white) ![DingTalk](https://img.shields.io/badge/DingTalk-Webhook-0089FF?logo=dingtalk&logoColor=white) ![Feishu](https://img.shields.io/badge/Feishu-Bot_API-00D6D9?logo=lark&logoColor=white) ![WeChat](https://img.shields.io/badge/WeChat-Enterprise-07C160?logo=wechat&logoColor=white) ![Email](https://img.shields.io/badge/Email-SMTP/IMAP-EA4335?logo=gmail&logoColor=white)

### Web Interface (Beta)

FinchBot provides a modern Web interface built with React, Vite, and FastAPI:

```bash
# Start the backend server
uv run finchbot serve

# In another terminal, start the frontend
cd web
npm install
npm run dev
```

The Web interface supports:
- Real-time chat via WebSocket
- Multi-session management (coming soon)
- Rich text rendering

### Command Line Interface

FinchBot provides a full-featured command line interface, three commands to get started:

```bash
# Step 1: Configure API keys and default model
uv run finchbot config

# Step 2: Manage your sessions
uv run finchbot sessions

# Step 3: Start chatting
uv run finchbot chat
```

| Feature | Description |
|---------|-------------|
| Environment Variables | All configurations can be set via environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.) |
| i18n Support | Built-in Chinese/English support, auto-detects system language |
| Auto Fallback | Web search automatically falls back through Tavily to Brave to DuckDuckGo |

---

## System Architecture

FinchBot is built on **LangChain v1.2** and **LangGraph v1.0**, serving as an Agent system with persistent memory, dynamic tool scheduling, and multi-platform messaging support.

### Overall Architecture

```mermaid
graph TB
    subgraph UI [User Interaction Layer]
        CLI[CLI Interface]
        Web[Web Interface]
        API[REST API]
        Channels[Multi-platform Channels<br/>Discord/DingTalk/Feishu]
    end

    subgraph Core [Agent Core]
        Agent[LangGraph Agent<br/>Decision Engine]
        Context[ContextBuilder<br/>Context Building]
        Tools[ToolRegistry<br/>11 Built-in Tools]
        Memory[MemoryManager<br/>Dual-layer Memory]
    end

    subgraph Infra [Infrastructure Layer]
        Storage[Dual-layer Storage<br/>SQLite + VectorStore]
        LLM[LLM Providers<br/>OpenAI/Anthropic/DeepSeek]
    end

    CLI --> Agent
    Web --> Agent
    API --> Agent
    Channels --> Agent

    Agent --> Context
    Agent <--> Tools
    Agent <--> Memory

    Memory --> Storage
    Agent --> LLM
```

### Data Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant C as Channel
    participant B as MessageBus
    participant F as AgentFactory
    participant A as Agent
    participant M as MemoryManager
    participant T as Tools
    participant L as LLM

    U->>C: Send Message
    C->>B: InboundMessage
    B->>F: Get/Create Agent
    F->>A: Return Compiled Agent
  
    Note over A: Build Context
    A->>M: Recall Relevant Memories
    M-->>A: Return Context
  
    A->>L: Send Request
    L-->>A: Stream Response
  
    alt Tool Call Needed
        A->>T: Execute Tool
        T-->>A: Return Result
        A->>L: Continue with Result
        L-->>A: Final Response
    end
  
    A->>M: Store New Memories
    A->>B: OutboundMessage
    B->>C: Route to Channel
    C->>U: Display Response
```

### Directory Structure

```
finchbot/
├── agent/              # Agent Core
│   ├── core.py        # Agent creation and execution
│   ├── factory.py     # AgentFactory for component assembly
│   ├── context.py     # ContextBuilder for prompt assembly
│   └── skills.py      # SkillsLoader for Markdown skills
├── channels/           # Multi-Platform Messaging
│   ├── base.py        # BaseChannel abstract class
│   ├── bus.py         # MessageBus async router
│   ├── manager.py     # ChannelManager coordinator
│   └── schema.py      # InboundMessage/OutboundMessage models
├── cli/                # CLI Interface
│   ├── chat_session.py
│   ├── config_manager.py
│   ├── providers.py
│   └── ui.py
├── config/             # Configuration Management
│   ├── loader.py
│   └── schema.py
├── constants.py        # Centralized constants
├── i18n/               # Internationalization
│   ├── loader.py      # Language detection and loading
│   └── locales/
├── memory/             # Memory System
│   ├── manager.py
│   ├── types.py
│   ├── services/       # Service Layer
│   │   ├── classification.py
│   │   ├── embedding.py
│   │   ├── importance.py
│   │   └── retrieval.py
│   ├── storage/        # Storage Layer
│   │   ├── sqlite.py
│   │   └── vector.py
│   └── vector_sync.py
├── providers/          # LLM Providers
│   └── factory.py
├── server/             # Web Server
│   ├── main.py        # FastAPI application
│   └── loop.py        # AgentLoop for WebSocket
├── sessions/           # Session Management
│   ├── metadata.py
│   ├── selector.py
│   └── title_generator.py
├── skills/             # Skill System
│   ├── skill-creator/
│   ├── summarize/
│   └── weather/
├── tools/              # Tool System
│   ├── base.py
│   ├── factory.py     # ToolFactory for tool creation
│   ├── registry.py
│   ├── filesystem.py
│   ├── memory.py
│   ├── shell.py
│   ├── web.py
│   ├── session_title.py
│   └── search/
└── utils/              # Utility Functions
    ├── cache.py       # File-based caching
    ├── logger.py
    └── model_downloader.py
```

---

## Core Components

### 1. Memory Architecture: Dual-Layer Storage and Agentic RAG

FinchBot implements an advanced **dual-layer memory architecture** that solves LLM context window limits and long-term forgetting issues.

#### Why Agentic RAG?

| Dimension | Traditional RAG | Agentic RAG (FinchBot) |
|-----------|-----------------|------------------------|
| Retrieval Trigger | Fixed pipeline | Agent autonomous decision |
| Retrieval Strategy | Single vector retrieval | Hybrid retrieval with dynamic weight adjustment |
| Memory Management | Passive storage | Active remember/recall/forget |
| Classification | None | Auto-classification and importance scoring |
| Update Mechanism | Full rebuild | Incremental sync |

#### Dual-Layer Storage Architecture

```mermaid
flowchart TB
    classDef businessLayer fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef serviceLayer fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef storageLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    MM[MemoryManager<br/>remember/recall/forget]:::businessLayer

    RS[RetrievalService<br/>Hybrid Retrieval + RRF]:::serviceLayer
    CS[ClassificationService<br/>Auto Classification]:::serviceLayer
    IS[ImportanceScorer<br/>Importance Scoring]:::serviceLayer
    ES[EmbeddingService<br/>FastEmbed Local]:::serviceLayer

    SQLite[(SQLiteStore<br/>Source of Truth<br/>Precise Query)]:::storageLayer
    Vector[(VectorStore<br/>ChromaDB<br/>Semantic Search)]:::storageLayer
    DS[DataSyncManager<br/>Incremental Sync]:::storageLayer

    MM --> RS & CS & IS
    RS --> SQLite & Vector
    CS --> SQLite
    IS --> SQLite
    ES --> Vector
    
    SQLite <--> DS <--> Vector
```

#### Hybrid Retrieval Strategy

FinchBot uses **Weighted RRF (Weighted Reciprocal Rank Fusion)** strategy:

```python
class QueryType(StrEnum):
    """Query type determines retrieval weights"""
    KEYWORD_ONLY = "keyword_only"      # Pure keyword (1.0/0.0)
    SEMANTIC_ONLY = "semantic_only"    # Pure semantic (0.0/1.0)
    FACTUAL = "factual"                # Factual (0.8/0.2)
    CONCEPTUAL = "conceptual"          # Conceptual (0.2/0.8)
    COMPLEX = "complex"                # Complex (0.5/0.5)
    AMBIGUOUS = "ambiguous"            # Ambiguous (0.3/0.7)
```

### 2. Dynamic Prompt System: User-Editable Agent Brain

FinchBot's prompt system uses **file system and modular assembly** design.

#### Bootstrap File System

```
~/.finchbot/
├── SYSTEM.md           # Role definition
├── MEMORY_GUIDE.md     # Memory usage guide
├── SOUL.md             # Personality settings
├── AGENT_CONFIG.md     # Agent configuration
└── workspace/
    └── skills/         # Custom skills
```

#### Prompt Loading Flow

```mermaid
flowchart TD
    classDef startEnd fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef file fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef output fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    A([Agent Startup]):::startEnd --> B[Load Bootstrap Files]:::process
    
    B --> C[SYSTEM.md]:::file
    B --> D[MEMORY_GUIDE.md]:::file
    B --> E[SOUL.md]:::file
    B --> F[AGENT_CONFIG.md]:::file

    C --> G[Assemble Prompt]:::process
    D --> G
    E --> G
    F --> G

    G --> H[Load Always-on Skills]:::process
    H --> I[Build Skill Summary XML]:::process
    I --> J[Generate Tool Docs]:::process
    J --> K[Inject Runtime Info]:::process
    K --> L[Complete System Prompt]:::output

    L --> M([Send to LLM]):::startEnd
```

### 3. Tool System: Code-Level Capability Extension

Tools are the bridge for Agent to interact with the external world. FinchBot provides 11 built-in tools with easy extension.

#### Tool System Architecture

```mermaid
flowchart TB
    classDef registry fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef builtin fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef custom fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    Registry[ToolRegistry<br/>Global Registration]:::registry

    subgraph Built-in [11 Built-in Tools]
        File[File System<br/>read/write/edit/list]:::builtin
        Shell[Shell<br/>exec with guardrails]:::builtin
        Web[Web Search<br/>Tavily/Brave/DDG]:::builtin
        Mem[Memory<br/>remember/recall/forget]:::builtin
        Title[Session Title<br/>Auto-generate]:::builtin
    end

    subgraph Custom [Custom Tools]
        CT1[Custom Tool 1]:::custom
        CT2[Custom Tool 2]:::custom
    end

    Registry --> File & Shell & Web & Mem & Title
    Registry --> CT1 & CT2
```

#### Built-in Tools Overview

| Tool | Description | Use Case |
|------|-------------|----------|
| read_file | Read file content | Code review, file analysis |
| write_file | Write file content | Code generation, document creation |
| edit_file | Edit file content | Code refactoring, text replacement |
| list_dir | List directory contents | Project exploration |
| exec | Execute shell command | System operations, git commands |
| web_search | Search the web | Information retrieval, fact checking |
| remember | Store memory | Long-term knowledge retention |
| recall | Retrieve memory | Context-aware information retrieval |
| forget | Delete memory | Memory management |
| generate_session_title | Generate session title | Auto-naming chat sessions |

#### Creating Custom Tools

```python
from finchbot.tools.base import FinchTool
from pydantic import Field

class MyTool(FinchTool):
    """Tool description"""
    name: str = "my_tool"
    description: str = "What this tool does"
    
    arg1: str = Field(description="Argument description")
    
    def _run(self, arg1: str) -> str:
        # Tool implementation
        return f"Result: {arg1}"
```

### 4. Skill System: Natural Language Capability Extension

Skills are FinchBot's unique **natural language extension mechanism**. Unlike Tools (code-level), Skills extend Agent capabilities through Markdown files.

#### Skill vs Tool

| Dimension | Tool | Skill |
|-----------|------|-------|
| Extension Level | Code | Natural Language |
| Implementation | Python class | Markdown file |
| Capability | Execute actions | Provide knowledge and workflows |
| Hot Reload | No (requires restart) | Yes (file change detection) |
| Use Case | File operations, API calls | Domain expertise, task templates |

#### Skill File Format

```markdown
---
name: weather
description: Get weather information for any city
alwaysOn: false
---

# Weather Skill

## Overview

This skill helps you get weather information for any city worldwide.

## Workflow

1. Identify the city mentioned by the user
2. Use web_search to find current weather
3. Summarize the weather information
4. Provide recommendations if needed

## Example

User: "What's the weather like in Beijing?"

Assistant: [Uses web_search to find Beijing weather, then responds]
```

### 5. Multi-Platform Channel System

FinchBot's channel system uses **MessageBus + ChannelManager** architecture for unified multi-platform support.

#### Channel Architecture

```mermaid
graph TB
    classDef channel fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef bus fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef agent fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    subgraph Channels [Channel Layer]
        CLI[CLI Channel]:::channel
        Web[WebSocket Channel]:::channel
        Discord[Discord Bot]:::channel
        Ding[DingTalk Bot]:::channel
        Feishu[Feishu Bot]:::channel
    end

    Bus[MessageBus<br/>Async Router]:::bus
    Manager[ChannelManager<br/>Lifecycle]:::bus

    Agent[Agent Core]:::agent

    CLI & Web & Discord & Ding & Feishu --> Bus
    Bus --> Manager
    Manager --> Agent
```

---

## Quick Start

### Prerequisites

- Python 3.13+
- UV package manager (recommended)
- API keys for LLM providers (OpenAI, Anthropic, or DeepSeek)

### Installation

```bash
# Clone the repository
git clone https://github.com/xt765/FinchBot.git
cd FinchBot

# Install dependencies with UV
uv sync

# Or use pip
pip install -e ".[dev]"
```

### Configuration

```bash
# Interactive configuration
uv run finchbot config

# Or set environment variables
export OPENAI_API_KEY="your-api-key"
export MODEL_NAME="gpt-4o"
```

### Start Chatting

```bash
# Start interactive chat
uv run finchbot chat

# With specific model
uv run finchbot chat --model claude-sonnet-4-20250514
```

---

## Tech Stack

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| LangChain | 1.2.10+ | LLM framework |
| LangGraph | 1.0.8+ | Agent workflow |
| FastEmbed | 0.6.0+ | Local embedding |
| ChromaDB | 0.6.0+ | Vector storage |
| FastAPI | 0.133.0+ | Web API |
| Pydantic | 2.11.0+ | Data validation |

### Development Tools

| Tool | Purpose |
|------|---------|
| Ruff | Linting and formatting |
| Basedpyright | Type checking |
| Pytest | Testing |
| Pre-commit | Git hooks |

---

## Extension Guide

### Creating Custom Tools

See [Tool Extension Guide](docs/en-US/guide/extension.md#tools)

### Creating Custom Skills

See [Skill Extension Guide](docs/en-US/guide/extension.md#skills)

### Adding New Channels

See [Channel Extension Guide](docs/en-US/guide/extension.md#channels)

---

## Documentation

- [Architecture](docs/en-US/architecture.md)
- [Usage Guide](docs/en-US/guide/usage.md)
- [Extension Guide](docs/en-US/guide/extension.md)
- [Development Guide](docs/en-US/development.md)
- [Deployment Guide](docs/en-US/deployment.md)
- [Contributing](docs/en-US/contributing.md)
- [API Reference](docs/en-US/api.md)

---

## License

FinchBot is released under the [MIT License](LICENSE).

---

## Acknowledgments

FinchBot is inspired by:
- [LangChain](https://github.com/langchain-ai/langchain) - LLM framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent workflows
- [Nanobot](https://github.com/ischaojie/nanobot) - Skill system design

---

**Built with care by [Xuantong765](https://github.com/xt765)**
