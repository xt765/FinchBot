<div align="center">
  <img src="https://i-blog.csdnimg.cn/direct/8abea218c2804256a17cc8f2d6c81630.jpeg" width="150" >
  <h1><strong>Xuantong 765 (xt765)</strong></h1>
  <p><strong>LLM Development Engineer | Communication University of China · Digital Media Technology</strong></p>
  <p>
    <a href="https://blog.csdn.net/Yunyi_Chi" target="_blank" style="text-decoration: none;">
      <span style="background-color: #f39c12; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block;">CSDN · Homepage |</span>
    </a>
    <a href="https://github.com/xt765" target="_blank" style="text-decoration: none; margin-left: 8px;">
      <span style="background-color: #24292e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block;">GitHub · Follow</span>
    </a>
  </p>
</div>

---

### **About the Author**

- **Focus Areas**: LLM Development / RAG Knowledge Base / AI Agent Implementation / Model Fine-tuning
- **Tech Stack**: Python | RAG (LangChain / Dify + Milvus) | FastAPI + Docker
- **Engineering**: Model engineering deployment, knowledge base construction & optimization, full-stack solutions

> **"Making AI interaction smarter, making technology implementation more efficient"**
> Welcome technical discussions and project cooperation!

---
# FinchBot - A Truly Flexible AI Agent Framework
![Banner](https://i-blog.csdnimg.cn/direct/89e72e3b66ff4adc8ab8aa90400385ef.png)


> Author: Xuantong 765 (xt765)
> Project: [GitHub - FinchBot](https://github.com/xt765/finchbot)
> Mirror: [Gitee - FinchBot](https://gitee.com/xt765/finchbot)


## Abstract

FinchBot is a lightweight, modular AI Agent framework built on **LangChain v1.2** and **LangGraph v1.0**. It's not just another LLM wrapper—it's a thoughtfully designed architecture focused on three core challenges:

1. **How to enable infinite Agent extensibility?** — Through a dual-layer extension mechanism of Skills and Tools
2. **How to give Agents real memory?** — Through a dual-layer storage architecture + Agentic RAG
3. **How to make Agent behavior customizable?** — Through a dynamic prompt file system

This article dives deep into FinchBot's architecture, showing you the birth of a production-ready Agent framework.

---

## 1. Why FinchBot?

With so many AI Agent frameworks out there, you might ask: Why FinchBot?

### 1.1 Pain Points of Existing Frameworks

| Pain Point | Traditional Approach | FinchBot Solution |
| :---: | :--- | :--- |
| **Hard to Extend** | Modify core code | Inherit base class or create Markdown files |
| **Fragile Memory** | Rely on LLM context window | Dual-layer persistent storage + semantic retrieval |
| **Rigid Prompts** | Hardcoded in source | File system with hot reloading |
| **Outdated Arch** | Old LangChain APIs | LangChain v1.2 + LangGraph v1.0 |

### 1.2 Design Philosophy

```mermaid
graph BT
    %% Styles
    classDef roof fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef pillar fill:#e3f2fd,stroke:#1565c0,stroke-width:1px,color:#0d47a1;
    classDef base fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    %% Roof
    Roof("🦅 <b>FinchBot Framework</b><br/>Lightweight • Flexible • Extensible"):::roof

    %% Pillars
    subgraph Pillars [Core Philosophy]
        direction LR
        P("🛡️ <b>Privacy First</b><br/>Local Embedding<br/>No Cloud Upload"):::pillar
        M("🧩 <b>Modularity</b><br/>Factory Pattern<br/>Decoupled"):::pillar
        D("❤️ <b>Dev Friendly</b><br/>Type Safety<br/>Rich Docs"):::pillar
        S("⚙️ <b>Stability</b><br/>Thread Safe<br/>Auto Retry"):::pillar
        O("📦 <b>Out of Box</b><br/>Zero Config<br/>Auto Fallback"):::pillar
    end

    %% Foundation
    Base("🏗️ <b>Tech Foundation</b><br/>LangChain v1.2 • LangGraph v1.0 • Python 3.13"):::base

    %% Connections
    Base === P & M & D & S & O
    P & M & D & S & O === Roof
```

### 1.3 Out-of-the-Box Experience

FinchBot is designed with **"Out of the Box"** as a core principle:

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
| :---: | :--- |
| **Three-Step Start** | `config` → `sessions` → `chat`, complete workflow |
| **Env Vars** | Configure via `OPENAI_API_KEY`, etc. |
| **Rich CLI** | Full-screen keyboard navigation |
| **i18n** | Built-in English/Chinese support |
| **Auto Fallback** | Web search: Tavily → Brave → DuckDuckGo |
| **Zero Config** | Just set API Key and run |

---

## 2. Architecture: Modularity & Factory Pattern

FinchBot uses the Factory Pattern to enhance flexibility and maintainability.

### 2.1 Core Components

```mermaid
graph TD
    %% Styles
    classDef core fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef factory fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef memory fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef tools fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef user fill:#ffebee,stroke:#c62828,stroke-width:2px;

    %% User Layer
    User([User]) --> CLI[CLI Interface]
    class User user
    class CLI user

    %% Factory Layer
    subgraph Factory_Layer [Factory Layer]
        AgentFactory[Agent Factory]
        ToolFactory[Tool Factory]
    end
    class AgentFactory,ToolFactory factory

    CLI --> AgentFactory
    AgentFactory --> Agent
    AgentFactory --> ToolFactory
    ToolFactory --> ToolSet

    %% Core Layer
    subgraph Agent_Core [Agent Core]
        Agent[Agent Brain]
        ContextBuilder[Context Builder]
        SystemPrompt[System Prompt]
        
        Agent --> ContextBuilder
        ContextBuilder --> SystemPrompt
    end
    class Agent,ContextBuilder,SystemPrompt core

    %% Memory System
    subgraph Memory_System [Memory System]
        MemoryMgr[Memory Manager]
        SQLite[(SQLite Storage)]
        Vector[(Vector Store)]
        Sync[Data Sync]
        
        MemoryMgr --> Retrieval[Retrieval Service]
        MemoryMgr --> Classification[Classification]
        Retrieval --> SQLite
        Retrieval --> Vector
        SQLite <--> Sync <--> Vector
    end
    class MemoryMgr,SQLite,Vector,Sync,Retrieval,Classification memory

    Agent --> MemoryMgr

    %% Tool Ecosystem
    subgraph Tool_Ecosystem [Tool Ecosystem]
        ToolSet[Tool Set]
        ToolRegistry[Tool Registry]
        
        ToolSet --> ToolRegistry
        ToolRegistry --> File[File Ops]
        ToolRegistry --> Web[Web Search]
        ToolRegistry --> Shell[Shell Exec]
        ToolRegistry --> Custom[Custom Skills]
    end
    class ToolSet,ToolRegistry,File,Web,Shell,Custom tools

    Agent --> ToolSet
```

### 2.2 Agent Factory

`AgentFactory` assembles a complete Agent instance, hiding initialization complexity.

```python
# Simple creation interface
agent, checkpointer, tools = AgentFactory.create_for_cli(
    session_id=session_id,
    workspace=ws_path,
    model=chat_model,
    config=config_obj,
)
```

### 2.3 Tool Factory

`ToolFactory` manages tool instantiation, handling dependencies and fallback logic.

Example: **Web Search Auto-Fallback** implementation:

```python
# ToolFactory logic
def _create_web_search_tool(self):
    # 1. Try Tavily (Best Quality)
    if self.config.tavily_api_key:
        return WebSearchTool(engine="tavily", ...)
    
    # 2. Try Brave (Privacy)
    if self.config.brave_api_key:
        return WebSearchTool(engine="brave", ...)
        
    # 3. Default DuckDuckGo (No Key)
    return WebSearchTool(engine="duckduckgo", ...)
```

---

## 3. Memory: Dual-Layer Storage + Agentic RAG

FinchBot implements advanced **dual-layer memory** to solve context limits and forgetting.

### 3.1 Why Agentic RAG?

| Dimension | Traditional RAG | Agentic RAG (FinchBot) |
| :---: | :--- | :--- |
| **Trigger** | Fixed pipeline | Agent decides |
| **Strategy** | Single vector | Hybrid + dynamic weights |
| **Management** | Passive | Active remember/recall/forget |
| **Classification** | None | Auto-classification + scoring |
| **Update** | Full rebuild | Incremental sync |

### 3.2 Dual-Layer Storage

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

1. **Structured Layer (SQLite)**: Source of Truth, stores full text, metadata, classification.
2. **Semantic Layer (Vector Store)**: ChromaDB + FastEmbed, enables fuzzy search.

### 3.3 Hybrid Retrieval Strategy

FinchBot uses **Weighted RRF (Weighted Reciprocal Rank Fusion)** to blend keyword and vector search results.

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

---

## 4. Dynamic Prompts: Editable Brain

FinchBot uses a **file system + modular assembly** approach for prompts.

### 4.1 Bootstrap Files

```
~/.finchbot/
├── SYSTEM.md           # Role definition
├── MEMORY_GUIDE.md     # Memory guide
├── SOUL.md             # Personality
├── AGENT_CONFIG.md     # Configuration
└── workspace/
    └── skills/         # Custom skills
```

### 4.2 Loading Flow

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

---

## 5. Skills & Tools: Infinite Extensibility

### 5.1 Tool System

Tools connect the Agent to the world. FinchBot provides 11 built-in tools.

#### Web Search: Three-Engine Fallback

| Priority | Engine | API Key | Features |
| :---: | :---: | :---: | :--- |
| 1 | **Tavily** | Required | Best quality, AI-optimized |
| 2 | **Brave** | Required | Privacy-friendly |
| 3 | **DuckDuckGo** | None | Always available |

### 5.2 Skill System

Skills are defined via Markdown files.

#### Killer Feature: Agent Auto-Creates Skills

> **Just tell the Agent what skill you want, and it creates it!**

```
User: Create a translation skill for Chinese to English.

Agent: Okay, creating translation skill...
       [Invokes skill-creator]
       ✅ Created skills/translator/SKILL.md
       You can now use translation!
```

---

## 6. LangChain 1.2 Practice

FinchBot is built on the latest stack.

### 6.1 Agent Creation

```python
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, SqliteSaver | MemorySaver]:
  
    # 1. Initialize checkpoint
    if use_persistent:
        checkpointer = SqliteSaver.from_conn_string(str(db_path))
    else:
        checkpointer = MemorySaver()
  
    # 2. Build system prompt
    system_prompt = build_system_prompt(workspace)
  
    # 3. Create Agent
    agent = create_agent(
        model=model,
        tools=list(tools) if tools else None,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )
  
    return agent, checkpointer
```

### 6.2 Supported Providers

| Provider | Models | Features |
| :---: | :--- | :--- |
| OpenAI | GPT-5, O3-mini | Best capability |
| Anthropic | Claude Sonnet 4.5 | Safety, long context |
| DeepSeek | DeepSeek Chat | Cost-effective |
| Gemini | Gemini 2.5 Flash | Google's latest |
| Groq | Llama 4 | Ultra-fast |
| Moonshot | Kimi K1.5 | Long context |

---

## 7. Summary

FinchBot is a thoughtfully designed Agent framework:

| Feature | Highlight |
| :---: | :--- |
| **Architecture** | Factory pattern, high cohesion |
| **Memory** | Dual-layer, Agentic RAG, Weighted RRF |
| **Prompts** | File system, hot reload, modular |
| **Tools** | Registry pattern, thread safe, auto fallback |
| **Skills** | Markdown definition, auto-create |
| **Stack** | LangChain v1.2, LangGraph v1.0 |
| **Experience** | Env vars, Rich CLI, i18n |

If you are looking for a framework that is:

* ✅ Privacy First
* ✅ Truly Persistent
* ✅ Production Ready
* ✅ Flexible & Extensible
* ✅ Modern Architecture
* ✅ Out of the Box

FinchBot is worth a try.

---

## Links

* 📦 **Project**: [GitHub - FinchBot](https://github.com/xt765/finchbot)
* 📖 **Docs**: [FinchBot Docs](https://github.com/xt765/finchbot/tree/main/docs)
* 💬 **Issues**: [GitHub Issues](https://github.com/xt765/finchbot/issues)

---

> If this helps you, please give it a Star ⭐️
