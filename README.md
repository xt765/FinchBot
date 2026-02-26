# FinchBot — A Lightweight, Flexible, and Infinitely Extensible AI Agent Framework

<p align="center">
  <img src="docs/image/image.png" alt="FinchBot Logo" width="600">
</p>

<p align="center">
  <em>Built on LangChain v1.2 & LangGraph v1.0<br>
  with persistent memory, dynamic prompts, and seamless tool integration</em>
</p>

<p align="center">🌐 <strong>Language</strong>: <a href="README.md">English</a> | <a href="README_CN.md">中文</a></p>

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
  <img src="https://img.shields.io/badge/Gitee-Officially_Recommended-red?style=flat-square&logo=gitee&logoColor=white" alt="Gitee Recommended">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Ruff-Formatter-orange?style=flat-square&logo=ruff" alt="Ruff">
  <img src="https://img.shields.io/badge/Basedpyright-TypeCheck-purple?style=flat-square&logo=python" alt="Basedpyright">
  <img src="https://img.shields.io/badge/Docker-Containerized-blue?style=flat-square&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square&logo=open-source-initiative" alt="License">
</p>

**FinchBot** is a lightweight, modular AI Agent framework built on **LangChain v1.2** and **LangGraph v1.0**. It's not just another LLM wrapper—it's a thoughtfully designed architecture focused on three core challenges:

1. **How to enable infinite Agent extensibility?** — Through a dual-layer extension mechanism of Skills and Tools
2. **How to give Agents real memory?** — Through a dual-layer storage architecture + Agentic RAG
3. **How to make Agent behavior customizable?** — Through a dynamic prompt file system

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

|           Pain Point           | Traditional Approach         | FinchBot Solution                                  |
| :-----------------------------: | :--------------------------- | :------------------------------------------------- |
|    **Hard to Extend**    | Requires modifying core code | Inherit base class or create Markdown files        |
|    **Fragile Memory**    | Relies on LLM context window | Dual-layer persistent storage + semantic retrieval |
|     **Rigid Prompts**     | Hardcoded in source code     | File system with hot reloading                     |
|     **Slow Startup**     | Synchronous blocking I/O     | Fully async + Thread pool concurrency              |
| **Outdated Architecture** | Based on old LangChain APIs  | LangChain v1.2 + LangGraph v1.0                    |

### Design Philosophy

```mermaid
graph BT
    classDef roof fill:#ffebee,stroke:#c62828,stroke-width:3px,color:#b71c1c,rx:10,ry:10;
    classDef pillar fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1,rx:8,ry:8;
    classDef base fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px,color:#1b5e20,rx:10,ry:10;

    Roof("FinchBot Framework<br/>Lightweight • Flexible • Extensible"):::roof

    subgraph Pillars [Core Philosophy]
        direction LR
        P("Privacy First<br/>Local Embedding<br/>No Cloud Upload"):::pillar
        M("Modularity<br/>Factory Pattern<br/>Decoupled Design"):::pillar
        D("Dev Friendly<br/>Type Safety<br/>Rich Documentation"):::pillar
        S("Fast Startup<br/>Fully Async<br/>Thread Pool"):::pillar
        O("Out of Box<br/>Zero Config<br/>Auto Fallback"):::pillar
    end

    Base("Tech Foundation<br/>LangChain v1.2 • LangGraph v1.0 • Python 3.13"):::base

    Base === P & M & D & S & O
    P & M & D & S & O === Roof
```

### Multi-Platform Messaging

FinchBot unified message routing architecture - develop once, reach everywhere:

![Web](https://img.shields.io/badge/Web-WebSocket-blue?logo=googlechrome&logoColor=white) ![Discord](https://img.shields.io/badge/Discord-Bot_API-5865F2?logo=discord&logoColor=white) ![DingTalk](https://img.shields.io/badge/DingTalk-Webhook-0089FF?logo=dingtalk&logoColor=white) ![Feishu](https://img.shields.io/badge/Feishu-Bot_API-00D6D9?logo=lark&logoColor=white) ![WeChat](https://img.shields.io/badge/WeChat-Enterprise-07C160?logo=wechat&logoColor=white) ![Email](https://img.shields.io/badge/Email-SMTP/IMAP-EA4335?logo=gmail&logoColor=white)

### Web Interface (Beta)

FinchBot provides a modern Web interface built with React + Vite + FastAPI:

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

|             Feature             | Description                                                                                               |
| :-----------------------------: | :-------------------------------------------------------------------------------------------------------- |
| **Environment Variables** | All configurations can be set via environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) |
|     **i18n Support**     | Built-in Chinese/English support, auto-detects system language                                            |
|     **Auto Fallback**     | Web search automatically falls back through Tavily → Brave → DuckDuckGo                                 |

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
├── constants.py        # Unified constants definition
├── i18n/               # Internationalization
│   ├── loader.py      # Language loader
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
    ├── cache.py       # Generic cache base class
    ├── logger.py
    └── model_downloader.py
```

---

## Core Components

### 1. Memory Architecture: Dual-Layer Storage + Agentic RAG

FinchBot implements an advanced **dual-layer memory architecture** that solves LLM context window limits and long-term forgetting issues.

#### Why Agentic RAG?

|          Dimension          | Traditional RAG         | Agentic RAG (FinchBot)                       |
| :--------------------------: | :---------------------- | :------------------------------------------- |
| **Retrieval Trigger** | Fixed pipeline          | Agent autonomous decision                    |
| **Retrieval Strategy** | Single vector retrieval | Hybrid retrieval + dynamic weight adjustment |
| **Memory Management** | Passive storage         | Active remember/recall/forget                |
|   **Classification**   | None                    | Auto-classification + importance scoring     |
|  **Update Mechanism**  | Full rebuild            | Incremental sync                             |

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

FinchBot's prompt system uses **file system + modular assembly** design.

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
    classDef agent fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#7b1fa2;

    TR[ToolRegistry<br/>Global Registry]:::registry
    Lock[Single-Lock Pattern<br/>Thread-Safe Singleton]:::registry

    File[File Operations<br/>read_file / write_file<br/>edit_file / list_dir]:::builtin
    Web[Network<br/>web_search / web_extract]:::builtin
    Memory[Memory<br/>remember / recall / forget]:::builtin
    System[System<br/>exec / session_title]:::builtin

    Inherit[Inherit FinchTool<br/>Implement _run]:::custom
    Register[Register to Registry]:::custom

    Agent[Agent Call]:::agent

    TR --> Lock
    Lock --> File & Web & Memory & System
    Lock --> Inherit --> Register

    File --> Agent
    Web --> Agent
    Memory --> Agent
    System --> Agent
    Register --> Agent
```

#### Built-in Tools

|      Category      | Tool              | Function                      |
| :----------------: | :---------------- | :---------------------------- |
| **File Ops** | `read_file`     | Read local files              |
|                    | `write_file`    | Write local files             |
|                    | `edit_file`     | Edit file content             |
|                    | `list_dir`      | List directory contents       |
| **Network** | `web_search`    | Web search (Tavily/Brave/DDG) |
|                    | `web_extract`   | Web content extraction        |
|  **Memory**  | `remember`      | Proactively store memories    |
|                    | `recall`        | Retrieve memories             |
|                    | `forget`        | Delete/archive memories       |
|  **System**  | `exec`          | Secure shell execution        |
|                    | `session_title` | Manage session titles         |

#### Web Search: Three-Engine Fallback Design

```mermaid
flowchart TD
    classDef check fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef engine fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef fallback fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;

    Start[Web Search Request]:::check
    
    Check1{TAVILY_API_KEY<br/>Set?}:::check
    Tavily[Tavily<br/>Best Quality<br/>AI-Optimized]:::engine
    
    Check2{BRAVE_API_KEY<br/>Set?}:::check
    Brave[Brave Search<br/>Privacy Friendly<br/>Large Free Tier]:::engine
    
    DDG[DuckDuckGo<br/>Zero Config<br/>Always Available]:::fallback

    Start --> Check1
    Check1 -->|Yes| Tavily
    Check1 -->|No| Check2
    Check2 -->|Yes| Brave
    Check2 -->|No| DDG
```

| Priority |         Engine         |   API Key   | Features                                |
| :------: | :--------------------: | :----------: | :-------------------------------------- |
|    1    |    **Tavily**    |   Required   | Best quality, AI-optimized, deep search |
|    2    | **Brave Search** |   Required   | Large free tier, privacy-friendly       |
|    3    |  **DuckDuckGo**  | Not required | Always available, zero config           |

**How it works**:

1. If `TAVILY_API_KEY` is set → Use Tavily (best quality)
2. Else if `BRAVE_API_KEY` is set → Use Brave Search
3. Else → Use DuckDuckGo (no API key needed, always works)

This design ensures **web search works out of the box** even without any API key configuration!

#### Session Title: Smart Naming, Out of the Box

The `session_title` tool embodies FinchBot's out-of-the-box philosophy:

|         Method         | Description                                                        | Example                                  |
| :---------------------: | :----------------------------------------------------------------- | :--------------------------------------- |
| **Auto Generate** | After 2-3 turns, AI automatically generates title based on content | "Python Async Programming Discussion"    |
| **Agent Modify** | Tell Agent "Change session title to XXX"                           | Agent calls tool to modify automatically |
| **Manual Rename** | Press `r` key in session manager to rename                       | User manually enters new title           |

This design lets users **manage sessions without technical details**—whether automatic or manual.

### 4. Skill System: Define Agent Capabilities with Markdown

Skills are FinchBot's unique innovation—**defining Agent capabilities through Markdown files**.

#### Key Feature: Agent Auto-Creates Skills

FinchBot includes a built-in **skill-creator** skill, the ultimate expression of the out-of-the-box philosophy:

> **Just tell the Agent what skill you want, and it will create it automatically!**

```
User: Help me create a translation skill that can translate Chinese to English

Agent: Okay, I'll create a translation skill for you...
       [Invokes skill-creator skill]
       ✅ Created skills/translator/SKILL.md
       You can now use the translation feature directly!
```

No manual file creation, no coding—**extend Agent capabilities with just one sentence**!

#### Skill File Structure

```
skills/
├── skill-creator/        # Skill creator (Built-in) - Core of out-of-the-box
│   └── SKILL.md
├── summarize/            # Intelligent summarization (Built-in)
│   └── SKILL.md
├── weather/              # Weather query (Built-in)
│   └── SKILL.md
└── my-custom-skill/      # Agent auto-created or user-defined
    └── SKILL.md
```

#### Core Design Highlights

|            Feature            | Description                                       |
| :---------------------------: | :------------------------------------------------ |
|  **Agent Auto-Create**  | Tell Agent your needs, auto-generates skill files |
|  **Dual Skill Source**  | Workspace skills first, built-in skills fallback  |
|  **Dependency Check**  | Auto-check CLI tools and environment variables    |
| **Cache Invalidation** | Smart caching based on file modification time     |
| **Progressive Loading** | Always-on skills first, others on demand          |

### 5. Channel System: Multi-Platform Messaging

FinchBot's Channel system provides unified messaging across multiple platforms.

```mermaid
flowchart LR
    classDef bus fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef manager fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef channel fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    Bus[MessageBus<br/>Inbound/Outbound Queues]:::bus
    CM[ChannelManager<br/>Channel Coordination]:::manager

    Web[Web<br/>WebSocket]:::channel
    Discord[Discord<br/>Bot API]:::channel
    DingTalk[DingTalk<br/>Webhook]:::channel
    Feishu[Feishu<br/>Bot API]:::channel
    WeChat[WeChat<br/>Enterprise]:::channel
    Email[Email<br/>SMTP/IMAP]:::channel

    Bus <--> CM
    CM <--> Web & Discord & DingTalk & Feishu & WeChat & Email
```

#### Channel Architecture

|         Component         | Description                                       |
| :-----------------------: | :------------------------------------------------ |
|   **BaseChannel**   | Abstract base class defining channel interface    |
|   **MessageBus**   | Async message router with inbound/outbound queues |
| **ChannelManager** | Coordinates multiple channels and message routing |
| **InboundMessage** | Standardized incoming message format              |
| **OutboundMessage** | Standardized outgoing message format              |

### 6. LangChain v1.2 Architecture Practice

FinchBot is built on **LangChain v1.2** and **LangGraph v1.0**, using the latest Agent architecture.

```python
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, SqliteSaver | MemorySaver]:

    # 1. Initialize checkpoint (persistent state)
    if use_persistent:
        checkpointer = SqliteSaver.from_conn_string(str(db_path))
    else:
        checkpointer = MemorySaver()

    # 2. Build system prompt
    system_prompt = build_system_prompt(workspace)

    # 3. Create Agent (using LangChain official API)
    agent = create_agent(
        model=model,
        tools=list(tools) if tools else None,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent, checkpointer
```

#### Supported LLM Providers

| Provider | Models                      | Features                  |
| :-------: | :-------------------------- | :------------------------ |
|  OpenAI  | GPT-5, GPT-5.2, O3-mini     | Best overall capability   |
| Anthropic | Claude Sonnet 4.5, Opus 4.6 | High safety, long context |
| DeepSeek | DeepSeek Chat, Reasoner     | Chinese, cost-effective   |
|  Gemini  | Gemini 2.5 Flash            | Google's latest           |
|   Groq   | Llama 4 Scout/Maverick      | Ultra-fast inference      |
| Moonshot | Kimi K1.5/K2.5              | Long context, Chinese     |

---

## Quick Start

### Prerequisites

|      Item      | Requirement             |
| :-------------: | :---------------------- |
|       OS       | Windows / Linux / macOS |
|     Python     | 3.13+                   |
| Package Manager | uv (Recommended)        |

### Installation

```bash
# Clone repository (choose one)
# Gitee (recommended for users in China)
git clone https://gitee.com/xt765/finchbot.git
# or GitHub
git clone https://github.com/xt765/finchbot.git

cd finchbot

# Install dependencies
uv sync
```

> **Note**: The embedding model (~95MB) will be automatically downloaded to the local cache when you run the application for the first time (e.g., `finchbot chat`). No manual intervention required.

<details>
<summary>Development Installation</summary>

For development, install with dev dependencies:

```bash
uv sync --extra dev
```

This includes: pytest, ruff, basedpyright

</details>

### Best Practice: Three Commands to Get Started

```bash
# Step 1: Configure API keys and default model
uv run finchbot config

# Step 2: Manage your sessions
uv run finchbot sessions

# Step 3: Start chatting
uv run finchbot chat
```

That's it! These three commands cover the complete workflow:

- `finchbot config` — Interactive configuration for LLM providers, API keys, and settings
- `finchbot sessions` — Full-screen session manager for creating, renaming, deleting sessions
- `finchbot chat` — Start or continue an interactive conversation

### Docker Deployment

FinchBot provides official Docker support for easy deployment:

```bash
# Clone repository
git clone https://github.com/xt765/finchbot.git
cd finchbot

# Create .env file with your API keys
cp .env.example .env
# Edit .env and add your API keys

# Build and run
docker-compose up -d

# Access the Web interface
# http://localhost:8000
```

| Feature | Description |
| :-----: | :---------- |
| **One-command Deploy** | `docker-compose up -d` |
| **Persistent Storage** | Workspace and model cache via volumes |
| **Health Check** | Built-in container health monitoring |
| **Multi-arch Support** | Works on x86_64 and ARM64 |

### Alternative: Environment Variables

```bash
# Or set environment variables directly
export OPENAI_API_KEY="your-api-key"
uv run finchbot chat
```

### Log Level Control

```bash
# Default: Show WARNING and above logs
finchbot chat

# Show INFO and above logs
finchbot -v chat

# Show DEBUG and above logs (debug mode)
finchbot -vv chat
```

### Optional: Download Local Embedding Model

```bash
# For memory system semantic search (optional but recommended)
uv run finchbot models download
```

### Create Custom Skill

```bash
# Create skill directory
mkdir -p ~/.finchbot/workspace/skills/my-skill

# Create skill file
cat > ~/.finchbot/workspace/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: My custom skill
metadata:
  finchbot:
    emoji: ✨
    always: false
---

# My Custom Skill

When user requests XXX, I should...
EOF
```

---

## Tech Stack

|       Layer       | Technology        | Version |
| :----------------: | :---------------- | :------: |
|   Core Language   | Python            |  3.13+  |
|  Agent Framework  | LangChain         | 1.2.10+ |
|  State Management  | LangGraph         |  1.0.8+  |
|  Data Validation  | Pydantic          |    v2    |
|   Vector Storage   | ChromaDB          |  0.5.0+  |
|  Local Embedding  | FastEmbed         |  0.4.0+  |
| Search Enhancement | BM25              |  0.2.2+  |
|   CLI Framework   | Typer             | 0.23.0+ |
|     Rich Text     | Rich              | 14.3.0+ |
|      Logging      | Loguru            |  0.7.3+  |
|   Configuration   | Pydantic Settings | 2.12.0+ |
|    Web Backend    | FastAPI           | 0.115.0+ |
|    Web Frontend    | React + Vite      |  Latest  |

---

## Extension Guide

### Adding New Tools

Inherit `FinchTool` base class, implement `_run()` method, then register with `ToolRegistry`.

### Adding New Skills

Create a `SKILL.md` file in `~/.finchbot/workspace/skills/{skill-name}/`.

### Adding New LLM Providers

Add a new Provider class in `providers/factory.py`.

### Adding New Languages

Add a new `.toml` file under `i18n/locales/`.

### Adding New Channels

Inherit `BaseChannel` class, implement required methods, register with `ChannelManager`.

---

## Key Advantages

|          Advantage          | Description                                                                |
| :--------------------------: | :------------------------------------------------------------------------- |
|   **Privacy First**   | Uses FastEmbed locally for vector generation, no cloud upload              |
|  **True Persistence**  | Dual-layer memory storage with semantic retrieval and precise queries      |
|  **Production Ready**  | Double-checked locking, auto-retry, timeout control mechanisms             |
| **Flexible Extension** | Inherit FinchTool or create SKILL.md to extend without modifying core code |
|   **Model Agnostic**   | Supports OpenAI, Anthropic, Gemini, DeepSeek, Moonshot, Groq, etc.         |
|    **Thread Safe**    | Tool registration uses double-checked locking pattern                      |
|   **Multi-Platform**   | Channel system supports Web, Discord, DingTalk, Feishu, WeChat, Email      |

---

## Documentation

| Document                                      | Description                   |
| :-------------------------------------------- | :---------------------------- |
| [User Guide](docs/en-US/guide/usage.md)          | CLI usage tutorial            |
| [API Reference](docs/en-US/api.md)               | API reference                 |
| [Configuration Guide](docs/en-US/config.md)      | Configuration options         |
| [Extension Guide](docs/en-US/guide/extension.md) | Adding tools/skills           |
| [Architecture](docs/en-US/architecture.md)       | System architecture           |
| [Deployment Guide](docs/en-US/deployment.md)     | Deployment instructions       |
| [Development Guide](docs/en-US/development.md)   | Development environment setup |
| [Contributing Guide](docs/en-US/contributing.md) | Contribution guidelines       |

---

## Contributing

Contributions are welcome! Please read the [Contributing Guide](docs/en-US/contributing.md) for more information.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Star History

If this project is helpful to you, please give it a Star ⭐️
