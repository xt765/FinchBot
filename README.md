# FinchBot (雀翎)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Check: BasedPyright](https://img.shields.io/badge/type%20check-BasedPyright-green.svg)](https://github.com/DetachHead/basedpyright)

**FinchBot** is a lightweight, modular AI Agent framework built on **LangChain v1.2** and **LangGraph v1.0**. It's not just another LLM wrapper—it's a thoughtfully designed architecture focused on three core challenges:

1. **How to enable infinite Agent extensibility?** — Through a dual-layer extension mechanism of Skills and Tools
2. **How to give Agents real memory?** — Through a dual-layer storage architecture + Agentic RAG
3. **How to make Agent behavior customizable?** — Through a dynamic prompt file system

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
|:---:|:---|:---|
| **Hard to Extend** | Requires modifying core code | Inherit base class or create Markdown files |
| **Fragile Memory** | Relies on LLM context window | Dual-layer persistent storage + semantic retrieval |
| **Rigid Prompts** | Hardcoded in source code | File system with hot reloading |
| **Outdated Architecture** | Based on old LangChain APIs | LangChain v1.2 + LangGraph v1.0 |

### Design Philosophy

```
Privacy First → Local Embedding, no cloud data upload
Modularity → Each component independently replaceable
Developer Friendly → Type safety + comprehensive documentation
Production Ready → Double-checked locking + auto-retry + timeout control
Out of the Box → Zero-config startup, automatic fallback, rich CLI
```

### Out-of-the-Box Experience

FinchBot is designed with **"Out of the Box"** as a core principle—no complex setup required:

**Three Commands to Get Started:**

```bash
# Step 1: Configure API keys and default model
uv run finchbot config

# Step 2: Manage your sessions
uv run finchbot sessions

# Step 3: Start chatting
uv run finchbot chat
```

| Feature | Description |
|:---:|:---|
| **Three-Step Start** | `config` → `sessions` → `chat`, complete workflow in three commands |
| **Environment Variables** | All configurations can be set via environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) |
| **Rich CLI Interface** | Full-screen keyboard navigation with ↑/↓ arrows, interactive selection |
| **i18n Support** | Built-in Chinese/English support, auto-detects system language |
| **Auto Fallback** | Web search automatically falls back through Tavily → Brave → DuckDuckGo |
| **Zero Config Start** | Just set API key and run `finchbot chat` |

---

## System Architecture

FinchBot is built on **LangChain v1.2** and **LangGraph v1.0**, serving as an Agent system with persistent memory and dynamic tool scheduling.

```mermaid
graph TD
    User[User] --> CLI[CLI Interface]
    CLI --> Agent[Agent Core]

    subgraph Core
        Planner[Planner]
        Executor[Executor]
        ContextBuilder[Context Builder]
        ConfigMgr[Configuration Manager]
    end

    Agent --> ContextBuilder
    ContextBuilder --> SystemPrompt[System Prompt]

    Agent --> MemoryMgr[Memory System]
    subgraph MemSys
        Manager[Memory Manager]
        SQLite[(SQLite Storage)]
        Vector[(ChromaDB Vector)]
        Sync[Data Sync]
        Classify[Classification Service]
        Importance[Importance Scoring]
        Retrieval[Retrieval Service]
    end

    Manager --> SQLite
    Manager --> Vector
    Manager --> Classify
    Manager --> Importance
    Manager --> Retrieval
    SQLite <--> Sync <--> Vector

    Agent --> ToolSet[Tool Ecosystem]
    subgraph ToolSys
        Registry[Tool Registry]
        File[File Operations]
        Web[Web Search]
        Shell[Shell Execution]
        Custom[Custom Tools]
    end

    Registry --> File
    Registry --> Web
    Registry --> Shell
    Registry --> Custom

    Agent --> I18n[Internationalization]
```

### Directory Structure

```
finchbot/
├── agent/              # Agent Core
│   ├── core.py        # Agent creation and execution
│   ├── context.py     # Context building
│   └── skills.py      # Skill system
├── cli/                # CLI Interface
│   ├── chat_session.py
│   ├── config_manager.py
│   ├── providers.py
│   └── ui.py
├── config/             # Configuration Management
│   ├── loader.py
│   └── schema.py
├── i18n/               # Internationalization
│   ├── loader.py
│   ├── detector.py
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
│   ├── registry.py
│   ├── filesystem.py
│   ├── memory.py
│   ├── shell.py
│   ├── web.py
│   ├── session_title.py
│   └── search/
└── utils/              # Utility Functions
    ├── logger.py
    └── model_downloader.py
```

---

## Core Components

### 1. Skill System: Define Agent Capabilities with Markdown

Skills are FinchBot's unique innovation—**defining Agent capabilities through Markdown files**.

#### Skill File Structure

```
skills/
├── skill-creator/        # Skill creator (Built-in)
│   └── SKILL.md
├── summarize/            # Intelligent summarization (Built-in)
│   └── SKILL.md
├── weather/              # Weather query (Built-in)
│   └── SKILL.md
└── my-custom-skill/      # Your custom skill
    └── SKILL.md
```

#### Skill Definition Format

```markdown
<!-- skills/weather/SKILL.md -->
---
name: weather
description: Query current weather and forecast (no API key required)
metadata:
  finchbot:
    emoji: 🌤️
    always: false
    requires:
      bins: [curl]
      env: []
---

# Weather Query Skill

## Functionality
Query weather information using wttr.in service...

## Usage
When user asks about weather...
```

#### Core Design Highlights

| Feature | Description |
|:---:|:---|
| **Dual Skill Source** | Workspace skills first, built-in skills fallback |
| **Dependency Check** | Auto-check CLI tools and environment variables |
| **Cache Invalidation** | Smart caching based on file modification time |
| **Progressive Loading** | Always-on skills first, others on demand |

### 2. Tool System: Code-Level Capability Extension

Tools are the bridge for Agent to interact with the external world. FinchBot provides 11 built-in tools with easy extension.

#### Built-in Tools

| Category | Tool | Function |
|:---:|:---|:---|
| **File Ops** | `read_file` | Read local files |
| | `write_file` | Write local files |
| | `edit_file` | Edit file content |
| | `list_dir` | List directory contents |
| **Network** | `web_search` | Web search (Tavily/Brave/DDG) |
| | `web_extract` | Web content extraction |
| **Memory** | `remember` | Proactively store memories |
| | `recall` | Retrieve memories |
| | `forget` | Delete/archive memories |
| **System** | `exec` | Secure shell execution |
| | `session_title` | Manage session titles |

#### Web Search: Three-Engine Fallback Design

FinchBot's web search tool features a clever **three-engine fallback mechanism**, giving users flexibility and out-of-the-box experience:

| Priority | Engine | API Key | Features |
|:---:|:---:|:---:|:---|
| 1 | **Tavily** | Required | Best quality, AI-optimized, deep search |
| 2 | **Brave Search** | Required | Large free tier, privacy-friendly |
| 3 | **DuckDuckGo** | Not required | Always available, zero config |

**How it works**:
1. If `TAVILY_API_KEY` is set → Use Tavily (best quality)
2. Else if `BRAVE_API_KEY` is set → Use Brave Search
3. Else → Use DuckDuckGo (no API key needed, always works)

This design ensures **web search works out of the box** even without any API key configuration!

#### Tool Registration Mechanism

```python
from finchbot.tools.base import FinchTool
from typing import Any, ClassVar

class MyCustomTool(FinchTool):
    """Custom tool example."""
    
    name: str = "my_custom_tool"
    description: str = "My custom tool description"
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "input_text": {
                "type": "string",
                "description": "Input text"
            }
        },
        "required": ["input_text"]
    }
    
    def _run(self, input_text: str) -> str:
        # Implement your logic
        return f"Result: {input_text}"
```

### 3. Memory Architecture: Dual-Layer Storage + Agentic RAG

FinchBot implements an advanced **dual-layer memory architecture** that solves LLM context window limits and long-term forgetting issues.

#### Why Agentic RAG?

| Dimension | Traditional RAG | Agentic RAG (FinchBot) |
|:---:|:---|:---|
| **Retrieval Trigger** | Fixed pipeline | Agent autonomous decision |
| **Retrieval Strategy** | Single vector retrieval | Hybrid retrieval + dynamic weight adjustment |
| **Memory Management** | Passive storage | Active remember/recall/forget |
| **Classification** | None | Auto-classification + importance scoring |
| **Update Mechanism** | Full rebuild | Incremental sync |

#### Dual-Layer Storage Architecture

```mermaid
flowchart TB
    subgraph Business[Business Layer]
        MM[MemoryManager]
    end
    
    subgraph Storage[Storage Layer]
        SQLite[SQLiteStore<br/>Source of Truth]
        Vector[VectorMemoryStore<br/>Semantic Retrieval]
    end
    
    subgraph Services[Service Layer]
        RS[RetrievalService<br/>Hybrid Retrieval]
        CS[ClassificationService<br/>Auto Classification]
        IS[ImportanceScorer<br/>Importance Scoring]
        DS[DataSyncManager<br/>Data Sync]
    end
    
    MM --> RS
    MM --> CS
    MM --> IS
    
    RS --> SQLite
    RS --> Vector
    
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

### 4. Dynamic Prompt System: User-Editable Agent Brain

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
    A[Agent Startup] --> B[Load Bootstrap Files]
    B --> C[SYSTEM.md]
    B --> D[MEMORY_GUIDE.md]
    B --> E[SOUL.md]
    B --> F[AGENT_CONFIG.md]
    
    C --> G[Assemble Prompt]
    D --> G
    E --> G
    F --> G
    
    G --> H[Load Always-on Skills]
    H --> I[Build Skill Summary XML]
    I --> J[Generate Tool Docs]
    J --> K[Inject Runtime Info]
    K --> L[Complete System Prompt]
    
    L --> M[Send to LLM]
```

### 5. LangChain v1.2 Architecture Practice

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

| Provider | Models | Features |
|:---:|:---|:---|
| OpenAI | GPT-4, GPT-4o, O1, O3 | Best overall capability |
| Anthropic | Claude 3.5/4 Sonnet, Opus | High safety, long context |
| DeepSeek | DeepSeek-V3, R1 | Chinese, cost-effective |
| Gemini | Gemini 2.0/2.5 Flash | Google's latest |
| Groq | Llama 4, Mixtral | Ultra-fast inference |
| Moonshot | Kimi K1.5/K2.5 | Long context, Chinese |

---

## Quick Start

### Prerequisites

| Item | Requirement |
|:---:|:---|
| OS | Windows / Linux / macOS |
| Python | 3.13+ |
| Package Manager | uv (Recommended) |

### Installation

```bash
# Clone repository
git clone https://github.com/xt765/finchbot.git
cd finchbot

# Install dependencies with uv
uv sync
```

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

### Alternative: Environment Variables

```bash
# Or set environment variables directly
export OPENAI_API_KEY="your-api-key"
uv run finchbot chat
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

| Layer | Technology | Version |
|:---:|:---|:---:|
| Core Language | Python | 3.13+ |
| Agent Framework | LangChain | 1.2.10+ |
| State Management | LangGraph | 1.0.8+ |
| Data Validation | Pydantic | v2 |
| Vector Storage | ChromaDB | 0.5.0+ |
| Local Embedding | FastEmbed | 0.4.0+ |
| Search Enhancement | BM25 | 0.2.2+ |
| CLI Framework | Typer | 0.23.0+ |
| Rich Text | Rich | 14.3.0+ |
| Logging | Loguru | 0.7.3+ |
| Configuration | Pydantic Settings | 2.12.0+ |

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

---

## Key Advantages

| Advantage | Description |
|:---:|:---|
| **Privacy First** | Uses FastEmbed locally for vector generation, no cloud upload |
| **True Persistence** | Dual-layer memory storage with semantic retrieval and precise queries |
| **Production Ready** | Double-checked locking, auto-retry, timeout control mechanisms |
| **Flexible Extension** | Inherit FinchTool or create SKILL.md to extend without modifying core code |
| **Model Agnostic** | Supports OpenAI, Anthropic, Gemini, DeepSeek, Moonshot, Groq, etc. |
| **Thread Safe** | Tool registration uses double-checked locking pattern |

---

## Documentation

| Document | Description |
|:---|:---|
| [User Guide](docs/en-US/guide/usage.md) | CLI usage tutorial |
| [API Reference](docs/en-US/api.md) | API reference |
| [Configuration Guide](docs/en-US/config.md) | Configuration options |
| [Extension Guide](docs/en-US/guide/extension.md) | Adding tools/skills |
| [Architecture](docs/en-US/architecture.md) | System architecture |
| [Deployment Guide](docs/en-US/deployment.md) | Deployment instructions |
| [Development Guide](docs/en-US/development.md) | Development environment setup |
| [Contributing Guide](docs/en-US/contributing.md) | Contribution guidelines |

---

## Contributing

Contributions are welcome! Please read the [Contributing Guide](docs/en-US/contributing.md) for more information.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Star History

If this project is helpful to you, please give it a Star ⭐️
