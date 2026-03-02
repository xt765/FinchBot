<div align="center"> 
  <img src="https://i-blog.csdnimg.cn/direct/8abea218c2804256a17cc8f2d6c81630.jpeg" width="150" > 
  <h1><strong>Xuantong 765</strong></h1> 
  <p><strong>LLM Development Engineer | Communication University of China · Digital Media Technology (Intelligent Interaction & Game Design)</strong></p> 
  <p> 
    <a href="https://blog.csdn.net/Yunyi_Chi" target="_blank" style="text-decoration: none;"> 
      <span style="background-color: #f39c12; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block;">CSDN · Profile |</span> 
    </a> 
    <a href="https://github.com/xt765" target="_blank" style="text-decoration: none; margin-left: 8px;"> 
      <span style="background-color: #24292e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block;">GitHub · Follow</span> 
    </a> 
  </p> 
</div> 

--- 

### **About the Author** 

- **Deep Focus**: LLM Development / RAG Knowledge Base / AI Agent Implementation / Model Fine-tuning 
- **Tech Stack**: Python | RAG (LangChain / Dify + Milvus) | FastAPI + Docker 
- **Engineering**: Model Deployment, Knowledge Base Optimization, Full-stack Solutions 

> **「Make AI interaction smarter, make technology implementation more efficient」** 
> Welcome for technical exchanges and project cooperation!

---

# FinchBot — A Lightweight, Flexible, Infinitely Extensible AI Agent Framework

<p align="center"> 
   <img src="https://i-blog.csdnimg.cn/direct/60cd5e5971cc4226977289a17a99dbae.png" alt="FinchBot Logo" width="600"> 
 </p>

<p align="center">
  <em>Built on LangChain v1.2 and LangGraph v1.0<br>
  With persistent memory, dynamic prompts, seamless tool integration</em>
</p>

**🎉 Gitee Official Recommended Project** — FinchBot has received official recommendation from Gitee!

---

## Abstract

**FinchBot** is a lightweight, modular AI Agent framework built on **LangChain v1.2** and **LangGraph v1.0**. It is not just another simple LLM wrapper, but a thoughtfully designed architecture focusing on three core challenges:

1. **How to make Agent infinitely extensible?** — Through dual-layer extension mechanism of Skills and Tools
2. **How to give Agents true memory?** — Through dual-layer storage architecture + Agentic RAG
3. **How to make Agent behavior customizable?** — Through dynamic prompt file system

---

## 1. Why Choose FinchBot?

### Pain Points of Existing Frameworks

|         Pain Point         | Traditional Solution         | FinchBot Solution                                        |
| :------------------------: | :--------------------------- | :------------------------------------------------------- |
|   **Difficult to extend**  | Modify core code             | Inherit FinchTool base class or create Markdown skill files |
|   **Fragile memory**       | Rely on LLM context window   | SQLite + Vector dual storage + Agentic RAG + Weighted RRF |
|  **Inflexible prompts**    | Hard-coded in source         | Bootstrap file system, user-customizable prompts, hot reload |
|   **Slow startup**          | Synchronous blocking load    | Full async + Thread pool concurrency, 3-5x faster startup |
|   **Outdated architecture**| Old LangChain API           | LangChain v1.2 + LangGraph v1.0 state graph orchestration |

### Design Philosophy

```mermaid
graph BT
    classDef roof fill:#ffebee,stroke:#c62828,stroke-width:3px,color:#b71c1c,rx:10,ry:10;
    classDef pillar fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1,rx:8,ry:8;
    classDef base fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px,color:#1b5e20,rx:10,ry:10;

    Roof("FinchBot Framework<br/>Lightweight • Flexible • Infinite Extension"):::roof

    subgraph Pillars [Core Philosophy]
        direction LR
        P("Privacy First<br/>Local Embedding<br/>Data Not Uploaded"):::pillar
        M("Modular<br/>Factory Pattern<br/>Component Decoupling"):::pillar
        D("Developer Friendly<br/>Type Safety<br/>Complete Docs"):::pillar
        S("Fast Startup<br/>Full Async<br/>Thread Pool"):::pillar
        O("Out of Box<br/>Zero Config<br/>Auto Fallback"):::pillar
    end

    Base("Tech Foundation<br/>LangChain v1.2 • LangGraph v1.0 • Python 3.13"):::base

    Base === P & M & D & S & O
    P & M & D & S & O === Roof
```

### Multi-Platform Messaging Support

FinchBot provides production-grade multi-platform support via [LangBot](https://github.com/langbot-app/LangBot):

**Supported Platforms**: QQ, WeChat (Official/Enterprise), Feishu, DingTalk, Discord, Telegram, Slack, LINE, KOOK, and 12+ more platforms

```bash
# Install LangBot
uvx langbot

# Access WebUI at http://localhost:5300
# Configure your platforms and connect to FinchBot
```

### MCP (Model Context Protocol) Support

FinchBot uses the official `langchain-mcp-adapters` library for MCP integration, supporting both **stdio** and **HTTP** transports:

```bash
# Install dependency
uv add langchain-mcp-adapters

# Configure MCP servers
finchbot config
# Select "MCP Configuration" option
```

MCP Features:
- Dynamic tool discovery and registration
- stdio and HTTP transports
- Standardized tool calling interface
- Support for multiple MCP servers

### Command Line Interface

FinchBot provides a fully functional CLI — four commands to get started:

```bash
# Step 1: Configure API Key and default model
uv run finchbot config

# Step 2: Manage sessions
uv run finchbot sessions

# Step 3: Start chatting
uv run finchbot chat

# Step 4: Manage scheduled tasks
uv run finchbot cron
```

|          Feature          | Description                                                                         |
| :----------------------: | :---------------------------------------------------------------------------------- |
| **Environment Variables** | All configurations can be set via env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) |
|    **i18n Support**     | Built-in Chinese/English support, auto-detects system language                    |
|    **Auto Fallback**    | Web search auto-fallback: Tavily → Brave → DuckDuckGo                             |
| **Scheduled Tasks** | Interactive Cron manager with keyboard navigation                                       |
| **Background Tasks** | Three-tool pattern for async execution of long-running tasks                            |

---

## 2. System Architecture

FinchBot is built on **LangChain v1.2** + **LangGraph v1.0**, an Agent system with persistent memory, dynamic tool scheduling, and multi-platform messaging support.

### Overall Architecture

```mermaid
graph TB
    classDef uiLayer fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef coreLayer fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef infraLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    subgraph UI [User Interaction Layer]
        CLI[CLI Interface]:::uiLayer
        Channels[Multi-Platform<br/>Discord/DingTalk/Feishu/WeChat/Email]:::uiLayer
    end

    subgraph Core [Agent Core Layer]
        Agent[LangGraph Agent<br/>Decision Engine]:::coreLayer
        Context[ContextBuilder<br/>Prompt Assembly]:::coreLayer
        Tools[ToolRegistry<br/>15 Built-in Tools + MCP]:::coreLayer
        Memory[MemoryManager<br/>Dual-Layer Memory]:::coreLayer
    end

    subgraph Infra [Infrastructure Layer]
        Storage[Dual-Layer Storage<br/>SQLite + VectorStore]:::infraLayer
        LLM[LLM Providers<br/>OpenAI/Anthropic/DeepSeek]:::infraLayer
    end

    CLI --> Agent
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
    A->>M: Recall Relevant Memory
    M-->>A: Return Context

    A->>L: Send Request
    L-->>A: Streaming Response

    alt Tool Calling Needed
        A->>T: Execute Tool
        T-->>A: Return Result
        A->>L: Continue Processing
        L-->>A: Final Response
    end

    A->>M: Store New Memory
    A->>B: OutboundMessage
    B->>C: Route to Channel
    C->>U: Display Response
```

### Directory Structure

```
finchbot/
├── agent/              # Agent Core
│   ├── core.py        # Agent creation and execution
│   ├── factory.py     # AgentFactory component assembly
│   ├── context.py     # ContextBuilder prompt assembly
│   ├── capabilities.py # CapabilitiesBuilder capability building
│   └── skills.py      # SkillsLoader Markdown skill loading
├── channels/           # Multi-platform messaging (via LangBot)
│   ├── base.py        # BaseChannel abstract base class
│   ├── bus.py         # MessageBus async router
│   ├── manager.py     # ChannelManager coordinator
│   ├── schema.py      # Message models
│   └── langbot_integration.py  # LangBot integration guide
├── cli/                # Command Line Interface
│   ├── chat_session.py
│   ├── config_manager.py
│   ├── providers.py
│   └── ui.py
├── config/             # Configuration Management
│   ├── loader.py
│   ├── schema.py      # Includes MCPConfig, ChannelsConfig
│   └── utils.py
├── constants.py        # Unified constants
├── i18n/               # Internationalization
│   ├── loader.py      # Language loader
│   └── locales/
├── memory/             # Memory System
│   ├── manager.py
│   ├── types.py
│   ├── services/       # Service Layer
│   ├── storage/        # Storage Layer
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
│   ├── factory.py     # ToolFactory (MCP tools via langchain-mcp-adapters)
│   ├── registry.py
│   ├── filesystem.py
│   ├── memory.py
│   ├── shell.py
│   ├── web.py
│   ├── session_title.py
│   └── search/
└── utils/              # Utilities
    ├── cache.py
    ├── logger.py
    └── model_downloader.py
```

---

## 3. Core Components

### 3.1 Memory Architecture: Dual-Layer Storage + Agentic RAG

FinchBot implements an advanced **dual-layer memory architecture**, completely solving LLM context window limitations and long-term memory forgetting problems.

#### Why Agentic RAG?

|     Comparison Dimension      | Traditional RAG     | Agentic RAG (FinchBot)          |
| :----------------------------: | :------------------ | :------------------------------ |
|      **Retrieval Trigger**   | Fixed flow         | Agent autonomous decision       |
|      **Retrieval Strategy**   | Single vector      | Hybrid + dynamic weights        |
|      **Memory Management**   | Passive storage    | Active remember/recall/forget   |
|       **Classification**      | None               | Auto classification + scoring   |
|       **Update Mechanism**    | Full rebuild       | Incremental sync                |

#### Dual-Layer Storage Architecture

```mermaid
flowchart TB
    classDef businessLayer fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef serviceLayer fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef storageLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    MM[MemoryManager<br/>remember/recall/forget]:::businessLayer

    RS[RetrievalService<br/>Hybrid + RRF]:::serviceLayer
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

### 3.2 Dynamic Prompt System: User-Editable Agent Brain

FinchBot's prompt system uses **file system + modular assembly** design.

#### Bootstrap File System

```
~/.finchbot/
├── config.json              # Main configuration file
└── workspace/
    ├── bootstrap/           # Bootstrap files directory
    │   ├── SYSTEM.md        # Role definition
    │   ├── MEMORY_GUIDE.md  # Memory usage guide
    │   ├── SOUL.md          # Soul settings (personality)
    │   └── AGENT_CONFIG.md  # Agent configuration
    ├── config/              # Configuration directory
    │   └── mcp.json         # MCP server configuration
    ├── generated/           # Auto-generated files
    │   ├── TOOLS.md         # Tool documentation
    │   └── CAPABILITIES.md  # Capabilities info
    ├── skills/              # Custom skills
    ├── memory/              # Memory storage
    └── sessions/            # Session data
```

#### Prompt Loading Process

```mermaid
flowchart TD
    classDef startEnd fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef file fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef output fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    A([Agent Start]):::startEnd --> B[Load Bootstrap Files]:::process

    B --> C[bootstrap/SYSTEM.md]:::file
    B --> D[bootstrap/MEMORY_GUIDE.md]:::file
    B --> E[bootstrap/SOUL.md]:::file
    B --> F[bootstrap/AGENT_CONFIG.md]:::file

    C --> G[Assemble Prompts]:::process
    D --> G
    E --> G
    F --> G

    G --> H[Load Always-On Skills]:::process
    H --> I[Build Skills Summary XML]:::process
    I --> J[Generate Tool Docs TOOLS.md]:::process
    J --> K[Generate Capabilities CAPABILITIES.md]:::process
    K --> L[Inject Runtime Info]:::process
    L --> M[Complete System Prompt]:::output

    M --> N([Send to LLM]):::startEnd
```

### 3.3 Tool System: Code-Level Capability Extension

Tools are the bridge between Agent and the external world. FinchBot provides 15 built-in tools with easy extensibility.

#### Tool System Architecture

```mermaid
flowchart TB
    classDef registry fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef builtin fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef mcp fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#7b1fa2;
    classDef agent fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    TR[ToolRegistry<br/>Global Registry]:::registry
    Lock[Single Lock<br/>Thread-Safe Singleton]:::registry

    subgraph BuiltIn [Built-in Tools - 15]
        File[File Operations<br/>read/write/edit/list]:::builtin
        Web[Network<br/>search/extract]:::builtin
        Memory[Memory<br/>remember/recall/forget]:::builtin
        System[System<br/>exec/session_title]:::builtin
        Config[Configuration<br/>configure_mcp/refresh_capabilities<br/>get_capabilities/get_mcp_config_path]:::builtin
    end

    subgraph MCP [MCP Tools - langchain-mcp-adapters]
        MCPConfig[MCPServerConfig<br/>stdio/HTTP Config]:::mcp
        MCPClient[MultiServerMCPClient<br/>Official Client]:::mcp
        MCPTools[MCP Tools<br/>External Tools]:::mcp
    end

    Agent[Agent Call]:::agent

    TR --> Lock
    Lock --> BuiltIn
    MCPConfig --> MCPClient --> MCPTools --> TR
    TR --> Agent
```

#### Built-in Tools Overview

|       Category       | Tool              | Function                       |
| :------------------: | :---------------- | :------------------------------ |
| **File Operations** | `read_file`     | Read local files               |
|                     | `write_file`    | Write local files              |
|                     | `edit_file`     | Edit file content              |
|                     | `list_dir`      | List directory contents        |
|  **Network**        | `web_search`    | Web search (Tavily/Brave/DDG)  |
|                     | `web_extract`   | Web content extraction         |
|  **Memory**         | `remember`      | Active memory storage          |
|                     | `recall`        | Memory retrieval               |
|                     | `forget`        | Delete/archive memory          |
|  **System**         | `exec`          | Safe shell command execution   |
|                     | `session_title` | Manage session title           |
|  **Configuration**  | `configure_mcp` | Dynamically configure MCP servers (supports enable/disable) |
|                     | `refresh_capabilities` | Refresh capabilities file |
|                     | `get_capabilities` | Get current capabilities  |
|                     | `get_mcp_config_path` | Get MCP config path   |

#### Web Search: Three-Engine Fallback Design

```mermaid
flowchart TD
    classDef check fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef engine fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef fallback fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;

    Start[Web Search Request]:::check

    Check1{TAVILY_API_KEY<br/>Set?}:::check
    Tavily[Tavily<br/>Best Quality<br/>AI Optimized]:::engine

    Check2{BRAVE_API_KEY<br/>Set?}:::check
    Brave[Brave Search<br/>Privacy Friendly<br/>Large Free Tier]:::engine

    DDG[DuckDuckGo<br/>Zero Config<br/>Always Available]:::fallback

    Start --> Check1
    Check1 -->|Yes| Tavily
    Check1 -->|No| Check2
    Check2 -->|Yes| Brave
    Check2 -->|No| DDG
```

| Priority |      Engine       | API Key | Features                                |
| :-------: | :---------------: | :------: | :-------------------------------------- |
|    1    |    **Tavily**    | Required | Best quality, AI optimized, deep search |
|    2    | **Brave Search** | Required | Large free tier, privacy friendly      |
|    3    |  **DuckDuckGo**  | Not required | Always available, zero config      |

**How it works**:

1. If `TAVILY_API_KEY` is set → Use Tavily (best quality)
2. Otherwise if `BRAVE_API_KEY` is set → Use Brave Search
3. Otherwise → Use DuckDuckGo (no API Key needed, always available)

This design ensures **web search works out of the box even without any API Key configured**!

#### Agent Self-Configuration: Dynamic MCP Management

FinchBot's Agent can autonomously manage MCP servers through the `configure_mcp` tool, enabling dynamic capability expansion without manual configuration file editing.

**Supported Operations**:

| Operation | Description |
| :--- | :--- |
| `add` | Add new MCP server |
| `update` | Update existing server configuration |
| `remove` | Delete MCP server |
| `enable` | Enable disabled MCP server |
| `disable` | Temporarily disable MCP server |
| `list` | List all configured servers |

**Dynamic Prompt Updates**:

When MCP configuration changes, the Agent can refresh capability descriptions through `refresh_capabilities`, ensuring the system prompt always reflects current capabilities.

```mermaid
flowchart LR
    classDef config fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef system fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef prompt fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    MCP[MCP Config<br/>configure_mcp]:::config --> Refresh[refresh_capabilities]:::system --> Builder[CapabilitiesBuilder<br/>Regenerate]:::system --> Write[CAPABILITIES.md]:::prompt --> Load[Next Session<br/>Auto-Load]:::prompt
```

### 3.4 Skill System: Define Agent Capabilities with Markdown

Skills are FinchBot's unique innovation — **define Agent capability boundaries using Markdown files**.

#### Killer Feature: Agent Auto-Creates Skills

FinchBot has a built-in **skill-creator** skill, the ultimate embodiment of the out-of-box philosophy:

> **Just tell the Agent what skill you want, and it will automatically create it!**

```
User: Help me create a translation skill that translates Chinese to English.

Agent: Sure, I'll create a translation skill for you...
       [Calling skill-creator skill]
       Created skills/translator/SKILL.md
       You can now use the translation feature!
```

No need to manually create files or write code — **one sentence extends Agent capabilities**!

#### Skill File Structure

```
skills/
├── skill-creator/        # Skill Creator (built-in) - Core feature
│   └── SKILL.md
├── summarize/            # Smart Summary (built-in)
│   └── SKILL.md
├── weather/              # Weather Query (built-in)
│   └── SKILL.md
└── my-custom-skill/      # Auto-created by Agent or user-defined
    └── SKILL.md
```

#### Core Design Highlights

|        Feature         | Description                                |
| :--------------------: | :---------------------------------------- |
| **Agent Auto-Create** | Tell Agent requirements, auto-generate   |
|  **Dual-Layer Source** | Workspace skills first, built-in backup |
|   **Dependency Check** | Auto-check CLI tools and env vars        |
|  **Cache Invalidation** | Based on file modification time        |
|   **Progressive Load** | Always-on skills first, on-demand others  |

### 3.5 Channel System: Multi-Platform Messaging Support

FinchBot provides production-grade multi-platform messaging support via [LangBot](https://github.com/langbot-app/LangBot).

```mermaid
flowchart LR
    classDef bus fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef manager fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef channel fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    FinchBot[FinchBot<br/>Agent Core]:::bus
    LangBot[LangBot<br/>Platform Layer]:::manager

    QQ[QQ]:::channel
    WeChat[WeChat]:::channel
    Feishu[Feishu]:::channel
    DingTalk[DingTalk]:::channel
    Discord[Discord]:::channel
    Telegram[Telegram]:::channel
    Slack[Slack]:::channel

    FinchBot <--> LangBot
    LangBot <--> QQ & WeChat & Feishu & DingTalk & Discord & Telegram & Slack
```

**LangBot Features**:
- **15k+ GitHub Stars**, actively maintained
- **Supports 12+ platforms**: QQ, WeChat, WeCom, Feishu, DingTalk, Discord, Telegram, Slack, LINE, KOOK, Satori
- **Built-in WebUI**: Visual configuration for all platforms
- **Plugin ecosystem**: Supports MCP and other extensions

### 3.6 LangChain 1.2 Architecture Practice

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

    # 1. Initialize checkpointer (persistent state)
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

|   Provider   | Models                        | Features              |
| :-----------: | :---------------------------- | :-------------------- |
|   OpenAI   | GPT-5, GPT-5.2, O3-mini      | Most capable         |
|  Anthropic  | Claude Sonnet 4.5, Opus 4.6  | High security, long  |
|  DeepSeek   | DeepSeek Chat, Reasoner       | Best value           |
|   Gemini   | Gemini 2.5 Flash              | Google's latest      |
|    Groq    | Llama 4 Scout/Maverick       | Fastest inference    |
|  Moonshot   | Kimi K1.5/K2.5               | Long context          |

---

## 4. Quick Start

### Prerequisites

|    Item    | Requirement                |
| :--------: | :------------------------ |
|    OS      | Windows / Linux / macOS  |
|  Python    | 3.13+                     |
|   Package Manager | uv (recommended)   |

### Installation Steps

```bash
# Clone repository (choose one)
# Gitee (recommended for China)
git clone https://gitee.com/xt765/FinchBot.git
# or GitHub
git clone https://github.com/xt765/FinchBot.git

cd finchbot

# Install dependencies
uv sync
```

> **Note**: The embedding model (~95MB) will be automatically downloaded to local on first run (e.g., running `finchbot chat`). No manual intervention needed.

### Best Practice: Three Steps to Start

```bash
# Step 1: Configure API Key and default model
uv run finchbot config

# Step 2: Manage your sessions
uv run finchbot sessions

# Step 3: Start chatting
uv run finchbot chat
```

That's it! These three commands cover the complete workflow:

- `finchbot config` — Interactive configuration of LLM provider, API keys, and settings
- `finchbot sessions` — Full-screen session manager, create/rename/delete sessions
- `finchbot chat` — Start or continue interactive dialogue

### Docker Deployment

FinchBot provides official Docker support for one-click deployment:

```bash
# Clone repository
git clone https://gitee.com/xt765/FinchBot.git
cd finchbot

# Create .env file and configure API keys
cp .env.example .env
# Edit .env to add your API keys

# Build and run
docker-compose up -d

# Use CLI
docker exec -it finchbot finchbot chat
```

|      Feature       | Description                              |
| :----------------: | :--------------------------------------- |
| **One-click deploy** | `docker-compose up -d`                 |
| **Persistent storage** | Manage workspace and cache via volumes |
|  **Health check**  | Built-in container health monitoring   |
| **Multi-arch**     | Supports x86_64 and ARM64              |

---

## 5. Tech Stack

|      Layer      | Technology              |  Version  |
| :-------------: | :--------------------- | :--------: |
|  Base Language  | Python                 |   3.13+    |
|  Agent Framework | LangChain              | 1.2.10+    |
|  State Management| LangGraph             |  1.0.8+    |
| Data Validation | Pydantic               |    v2      |
| Vector Store    | ChromaDB               |  0.5.0+    |
| Local Embedding | FastEmbed              |  0.4.0+    |
| Search Enhance  | BM25                   |  0.2.2+    |
|  CLI Framework  | Typer                  | 0.23.0+    |
|    Rich Text    | Rich                   |  14.3+     |
|     Logging     | Loguru                 |  0.7.3+    |
|  Config Manage  | Pydantic Settings     | 2.12.0+    |

---

## 6. Project Advantages

|       Advantage        | Description                                                                 |
| :-------------------: | :-------------------------------------------------------------------------- |
|   **Privacy First**   | Using FastEmbed for local vector generation, no data uploaded to cloud     |
|  **True Persistence** | Dual-layer memory storage architecture, supports semantic and precise query |
|  **Production Ready** | Single lock mode, auto-retry, timeout control                               |
|  **Flexible Extension** | Inherit FinchTool or create SKILL.md to extend, no core code changes      |
|  **Model Agnostic**   | Supports OpenAI, Anthropic, Gemini, DeepSeek, Moonshot, Groq, etc.        |
|   **Thread Safe**     | Tool registry uses single lock mode, thread-safe                           |
| **Multi-Platform**    | Via LangBot supports QQ, WeChat, Feishu, DingTalk, Discord, Telegram, Slack and 12+ platforms |
| **MCP Support**       | Via official langchain-mcp-adapters supporting stdio and HTTP transports |
| **Agent Autonomy** | Agent can self-execute tasks, self-create plans, self-extend capabilities |
| **Background Tasks** | Three-tool pattern for async execution of long-running tasks |
| **Scheduled Tasks** | Cron expression based scheduling with interactive CLI management |
| **Heartbeat Service** | Background monitoring and automatic task triggering |

---

## 4. Agent Autonomy Architecture

**Core Philosophy**: FinchBot is designed to give agents **true autonomy**—not just responding to user requests, but self-deciding, self-executing, and self-extending.

### Autonomy Pyramid

```mermaid
graph BT
    classDef level1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef level2 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef level3 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;
    classDef level4 fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    L1[Response Layer<br/>Respond to User]:::level1
    L2[Execution Layer<br/>Self-Execute Tasks]:::level2
    L3[Planning Layer<br/>Self-Create Plans]:::level3
    L4[Extension Layer<br/>Self-Extend Capabilities]:::level4

    L1 --> L2 --> L3 --> L4
```

| Layer | Capability | Implementation | User Value |
|:---:|:---|:---|:---|
| **Response Layer** | Respond to user requests | Dialog system + Tool calls | Basic interaction |
| **Execution Layer** | Self-execute tasks | Background task system | Non-blocking dialog |
| **Planning Layer** | Self-create plans | Scheduled tasks + Heartbeat | Automated execution |
| **Extension Layer** | Self-extend capabilities | MCP config + Skill creation | Infinite extension |

### Autonomy Comparison

| Capability | Traditional Agent | FinchBot Autonomous Agent |
|:---|:---|:---|
| **Task Execution** | User-triggered, blocking wait | Agent self-starts background tasks |
| **Task Scheduling** | User manually sets | Agent self-creates scheduled tasks |
| **Self-Monitoring** | None | Heartbeat service self-checks status |
| **Capability Extension** | Developer writes code | Agent self-configures MCP |
| **Behavior Definition** | Hardcoded prompts | Agent self-creates skills |

### Background Task System (Subagent)

FinchBot implements an advanced background task system using a **three-tool pattern** that allows agents to asynchronously execute long-running tasks.

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant BG as Background Task System
    participant S as Subagent

    U->>A: Execute long task
    A->>BG: start_background_task
    BG->>S: Create independent Agent
    BG-->>A: Return job_id
    A-->>U: Task started (ID: xxx)
    
    Note over U,A: User continues dialog...
    
    U->>A: Other questions
    A-->>U: Normal response
    
    U->>A: Task progress?
    A->>BG: check_task_status
    BG-->>A: running
    A-->>U: Still executing...
    
    S-->>BG: Task complete
    U->>A: Get result
    A->>BG: get_task_result
    BG-->>A: Return result
    A-->>U: Task result display
```

| Tool | Function | Agent Autonomy |
|:---|:---|:---|
| `start_background_task` | Start background task | Agent self-determines if background execution needed |
| `check_task_status` | Check task status | Agent self-decides when to check |
| `get_task_result` | Get task result | Agent self-decides when to get result |
| `cancel_task` | Cancel task | Agent self-decides whether to cancel |

### Scheduled Task System (Cron)

FinchBot provides a complete scheduled task solution supporting both **CLI interactive management** and **tool calls**.

**Cron Expression Examples**:

| Expression | Description |
|:---|:---|
| `0 9 * * *` | Daily at 9:00 AM |
| `0 */2 * * *` | Every 2 hours |
| `30 18 * * 1-5` | Weekdays at 6:30 PM |
| `0 0 1 * *` | First day of month at midnight |

**Interactive Interface**:

| Key | Action |
|:---:|:---|
| ↑ / ↓ | Navigate task list |
| Enter | View task details |
| n | Create new task |
| d | Delete selected task |
| e | Enable/disable task |
| r | Execute immediately |
| q | Quit management |

### Heartbeat Service

The heartbeat service is FinchBot's background monitoring service, implementing automated task triggering through periodic reading of the `HEARTBEAT.md` file.

```mermaid
flowchart LR
    classDef heartbeat fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef cron fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef background fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;
    classDef notify fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    H[HeartbeatService]:::heartbeat
    C[CronService]:::cron
    B[BackgroundTasks]:::background
    N[Notification System]:::notify

    H --> |Trigger execution| C
    H --> |Check status| B
    H --> |Send reminder| N
```

### MCP Self-Configuration

**Core Philosophy**: Enable agents to autonomously configure MCP servers, dynamically extending their tool capabilities.

```mermaid
flowchart TB
    classDef need fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef config fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef tool fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef use fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;

    Need[Agent Discovers Need<br/>"I need database capability"]:::need
    Search[Search Available MCP Servers]:::config
    Config[configure_mcp<br/>Self-Configure]:::config
    Load[Dynamically Load New Tools]:::tool
    Use[Agent Uses New Tools]:::use

    Need --> Search --> Config --> Load --> Use
```

**Agent Self-Extension Example**:

```
User: Help me analyze this SQLite database

Agent thinks:
1. Current tool check: No database operation tools
2. Capability gap: Need SQLite operation capability
3. Solution: Configure SQLite MCP server

Agent acts:
1. Call configure_mcp(action="add", server_name="sqlite", ...)
2. Call refresh_capabilities() to refresh capability description
3. New tools auto-loaded: query_sqlite, list_tables, ...

Agent uses new capability:
1. Call list_tables() to view schema
2. Call query_sqlite("SELECT * FROM users LIMIT 10")
3. Return to user: Database analysis results...
```

---

## Links

- **Project**: [GitHub - FinchBot](https://github.com/xt765/FinchBot) | [Gitee - FinchBot](https://gitee.com/xt765/FinchBot)
- **Documentation**: [FinchBot Docs](https://github.com/xt765/FinchBot/tree/main/docs)
- **Issues**: [GitHub Issues](https://github.com/xt765/FinchBot/issues)

---

> If this is helpful, please give a Star⭐ to support!
