# FinchBot (雀翎) —— 轻量灵活，无限扩展的 AI Agent 框架

<p align="center">
  <img src="docs/image/image.png" alt="FinchBot Logo" width="600">
</p>

<p align="center">
  <em>基于 LangChain v1.2 与 LangGraph v1.0 构建<br>
  具备持久记忆、动态提示词、无缝工具集成</em>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Check: BasedPyright](https://img.shields.io/badge/type%20check-BasedPyright-green.svg)](https://github.com/DetachHead/basedpyright)

**FinchBot (雀翎)** 是一个轻量级、模块化的 AI Agent 框架，基于 **LangChain v1.2** 和 **LangGraph v1.0** 构建。它不是又一个简单的 LLM 封装，而是一个深思熟虑的架构设计，专注于三个核心问题：

1. **如何让 Agent 的能力无限扩展？** — 通过技能 (Skill) 和工具 (Tool) 的双层扩展机制
2. **如何让 Agent 拥有真正的记忆？** — 通过双层存储架构 + Agentic RAG
3. **如何让 Agent 的行为可定制？** — 通过动态提示词文件系统

[中文文档](docs/zh-CN/README.md) | [English Documentation](README.md)

## 目录

1. [为什么选择 FinchBot？](#为什么选择-finchbot)
2. [系统架构](#系统架构)
3. [核心组件](#核心组件)
4. [快速开始](#快速开始)
5. [技术栈](#技术栈)
6. [扩展指南](#扩展指南)
7. [文档](#文档)

---

## 为什么选择 FinchBot？

### 现有框架的痛点

|         痛点         | 传统方案                | FinchBot 方案                   |
| :------------------: | :---------------------- | :------------------------------ |
|  **扩展困难**  | 需要修改核心代码        | 继承基类或创建 Markdown 文件    |
|  **记忆脆弱**  | 依赖 LLM 上下文窗口     | 双层持久化存储 + 语义检索       |
| **提示词僵化** | 硬编码在代码中          | 文件系统，热加载                |
|  **架构过时**  | 基于 LangChain 旧版 API | LangChain v1.2 + LangGraph v1.0 |

### 设计哲学

```mermaid
graph BT
    %% 样式定义
    classDef roof fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef pillar fill:#e3f2fd,stroke:#1565c0,stroke-width:1px,color:#0d47a1;
    classDef base fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    %% 顶层
    Roof("🦅 <b>FinchBot Framework</b><br/>轻量 • 灵活 • 无限扩展"):::roof

    %% 支柱
    subgraph Pillars [核心哲学]
        direction LR
        P("🛡️ <b>隐私优先</b><br/>本地 Embedding<br/>数据不上云"):::pillar
        M("🧩 <b>模块化</b><br/>工厂模式<br/>组件解耦"):::pillar
        D("❤️ <b>开发者友好</b><br/>类型安全<br/>文档完善"):::pillar
        S("⚙️ <b>生产级稳定</b><br/>双重锁机制<br/>自动重试"):::pillar
        O("📦 <b>开箱即用</b><br/>零配置启动<br/>自动降级"):::pillar
    end

    %% 底层
    Base("🏗️ <b>技术基石</b><br/>LangChain v1.2 • LangGraph v1.0 • Python 3.13"):::base

    %% 连接
    Base === P & M & D & S & O
    P & M & D & S & O === Roof
```

### 开箱即用体验

FinchBot 将 **"开箱即用"** 作为核心设计理念——无需复杂配置即可上手：

**三步快速上手：**

```bash
# 第一步：配置 API 密钥和默认模型
uv run finchbot config

# 第二步：管理你的会话
uv run finchbot sessions

# 第三步：开始对话
uv run finchbot chat
```

|          特性          | 说明                                                                         |
| :---------------------: | :--------------------------------------------------------------------------- |
|   **三步上手**   | `config` → `sessions` → `chat`，三个命令完成完整工作流程             |
| **环境变量配置** | 所有配置均可通过环境变量设置（`OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 等） |
| **Rich CLI 界面** | 全屏键盘导航，↑/↓ 箭头选择，交互式操作                                     |
|  **i18n 国际化**  | 内置中英文支持，自动检测系统语言                                             |
|   **自动降级**   | 网页搜索自动降级：Tavily → Brave → DuckDuckGo                              |
|  **零配置启动**  | 只需设置 API Key，运行 `finchbot chat` 即可                                |

---

## 系统架构

FinchBot 采用 **LangChain v1.2** + **LangGraph v1.0** 构建，是一个具备持久化记忆和动态工具调度的 Agent 系统。

```mermaid
graph TD
    %% 样式定义
    classDef core fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef factory fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef memory fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef tools fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef user fill:#ffebee,stroke:#c62828,stroke-width:2px;

    %% 用户交互层
    User([用户]) --> CLI[命令行界面]
    class User user
    class CLI user

    %% 工厂层
    subgraph Factory_Layer [工厂层]
        AgentFactory[Agent Factory]
        ToolFactory[Tool Factory]
    end
    class AgentFactory,ToolFactory factory

    CLI --> AgentFactory
    AgentFactory --> Agent
    AgentFactory --> ToolFactory
    ToolFactory --> ToolSet

    %% 核心层
    subgraph Agent_Core [Agent 核心]
        Agent[Agent 大脑]
        ContextBuilder[上下文构建器]
        SystemPrompt[系统提示词]
        
        Agent --> ContextBuilder
        ContextBuilder --> SystemPrompt
    end
    class Agent,ContextBuilder,SystemPrompt core

    %% 记忆系统
    subgraph Memory_System [记忆系统]
        MemoryMgr[记忆管理器]
        SQLite[(SQLite 存储)]
        Vector[(向量存储)]
        Sync[数据同步]
        
        MemoryMgr --> Retrieval[检索服务]
        MemoryMgr --> Classification[自动分类]
        Retrieval --> SQLite
        Retrieval --> Vector
        SQLite <--> Sync <--> Vector
    end
    class MemoryMgr,SQLite,Vector,Sync,Retrieval,Classification memory

    Agent --> MemoryMgr

    %% 工具系统
    subgraph Tool_Ecosystem [工具生态]
        ToolSet[工具集]
        ToolRegistry[工具注册表]
        
        ToolSet --> ToolRegistry
        ToolRegistry --> File[文件操作]
        ToolRegistry --> Web[网络搜索]
        ToolRegistry --> Shell[Shell 执行]
        ToolRegistry --> Custom[自定义技能]
    end
    class ToolSet,ToolRegistry,File,Web,Shell,Custom tools

    Agent --> ToolSet
```

### 目录结构

```
finchbot/
├── agent/              # Agent 核心
│   ├── core.py        # Agent 创建与运行
│   ├── context.py     # 上下文构建
│   └── skills.py      # 技能系统
├── cli/                # 命令行界面
│   ├── chat_session.py
│   ├── config_manager.py
│   ├── providers.py
│   └── ui.py
├── config/             # 配置管理
│   ├── loader.py
│   └── schema.py
├── i18n/               # 国际化
│   ├── loader.py
│   ├── detector.py
│   └── locales/
├── memory/             # 记忆系统
│   ├── manager.py
│   ├── types.py
│   ├── services/       # 服务层
│   │   ├── classification.py
│   │   ├── embedding.py
│   │   ├── importance.py
│   │   └── retrieval.py
│   ├── storage/        # 存储层
│   │   ├── sqlite.py
│   │   └── vector.py
│   └── vector_sync.py
├── providers/          # LLM 提供商
│   └── factory.py
├── sessions/           # 会话管理
│   ├── metadata.py
│   ├── selector.py
│   └── title_generator.py
├── skills/             # 技能系统
│   ├── skill-creator/
│   ├── summarize/
│   └── weather/
├── tools/              # 工具系统
│   ├── base.py
│   ├── registry.py
│   ├── filesystem.py
│   ├── memory.py
│   ├── shell.py
│   ├── web.py
│   ├── session_title.py
│   └── search/
└── utils/              # 工具函数
    ├── logger.py
    └── model_downloader.py
```

---

## 核心组件

### 1. 记忆架构：双层存储 + Agentic RAG

FinchBot 实现了先进的**双层记忆架构**，彻底解决了 LLM 上下文窗口限制和长期记忆遗忘问题。

#### 为什么是 Agentic RAG？

|      对比维度      | 传统 RAG     | Agentic RAG (FinchBot)      |
| :----------------: | :----------- | :-------------------------- |
| **检索触发** | 固定流程     | Agent 自主决策              |
| **检索策略** | 单一向量检索 | 混合检索 + 权重动态调整     |
| **记忆管理** | 被动存储     | 主动 remember/recall/forget |
| **分类能力** | 无           | 自动分类 + 重要性评分       |
| **更新机制** | 全量重建     | 增量同步                    |

#### 双层存储架构

```mermaid
flowchart TB
    subgraph Business[业务层]
        MM[MemoryManager]
    end
  
    subgraph Storage[存储层]
        SQLite[SQLiteStore<br/>真相源]
        Vector[VectorMemoryStore<br/>语义检索]
    end
  
    subgraph Services[服务层]
        RS[RetrievalService<br/>混合检索]
        CS[ClassificationService<br/>自动分类]
        IS[ImportanceScorer<br/>重要性评分]
        DS[DataSyncManager<br/>数据同步]
    end
  
    MM --> RS
    MM --> CS
    MM --> IS
  
    RS --> SQLite
    RS --> Vector
  
    SQLite <--> DS <--> Vector
```

#### 混合检索策略

FinchBot 采用**加权 RRF (Weighted Reciprocal Rank Fusion)** 策略：

```python
class QueryType(StrEnum):
    """查询类型，决定检索权重"""
    KEYWORD_ONLY = "keyword_only"      # 纯关键词 (1.0/0.0)
    SEMANTIC_ONLY = "semantic_only"    # 纯语义 (0.0/1.0)
    FACTUAL = "factual"                # 事实型 (0.8/0.2)
    CONCEPTUAL = "conceptual"          # 概念型 (0.2/0.8)
    COMPLEX = "complex"                # 复杂型 (0.5/0.5)
    AMBIGUOUS = "ambiguous"            # 歧义型 (0.3/0.7)
```

### 2. 动态提示词系统：用户可编辑的 Agent 大脑

FinchBot 的提示词系统采用**文件系统 + 模块化组装**的设计。

#### Bootstrap 文件系统

```
~/.finchbot/
├── SYSTEM.md           # 角色设定
├── MEMORY_GUIDE.md     # 记忆使用指南
├── SOUL.md             # 灵魂设定（性格特征）
├── AGENT_CONFIG.md     # Agent 配置
└── workspace/
    └── skills/         # 自定义技能
```

#### 提示词加载流程

```mermaid
flowchart TD
    A[Agent 启动] --> B[加载 Bootstrap 文件]
    B --> C[SYSTEM.md]
    B --> D[MEMORY_GUIDE.md]
    B --> E[SOUL.md]
    B --> F[AGENT_CONFIG.md]
  
    C --> G[组装提示词]
    D --> G
    E --> G
    F --> G
  
    G --> H[加载常驻技能]
    H --> I[构建技能摘要 XML]
    I --> J[生成工具文档]
    J --> K[注入运行时信息]
    K --> L[完整系统提示]
  
    L --> M[发送给 LLM]
```

### 3. 工具系统：代码级能力扩展

工具是 Agent 与外部世界交互的桥梁。FinchBot 提供了 11 个内置工具，并支持轻松扩展。

#### 工具系统架构

```mermaid
flowchart TB
    subgraph Registry[工具注册中心]
        TR[ToolRegistry<br/>全局注册表]
        Lock[双重检查锁<br/>线程安全]
    end
  
    subgraph BuiltIn[内置工具 - 11个]
        File[文件操作<br/>read/write/edit/list]
        Web[网络能力<br/>search/extract]
        Memory[记忆管理<br/>remember/recall/forget]
        System[系统控制<br/>exec/session_title]
    end
  
    subgraph Custom[自定义扩展]
        Inherit[继承 FinchTool]
        Register[注册到 Registry]
    end
  
    TR --> Lock
    Lock --> BuiltIn
    Lock --> Custom
  
    File --> Agent[Agent 调用]
    Web --> Agent
    Memory --> Agent
    System --> Agent
```

#### 内置工具一览

|        类别        | 工具              | 功能                        |
| :----------------: | :---------------- | :-------------------------- |
| **文件操作** | `read_file`     | 读取本地文件                |
|                    | `write_file`    | 写入本地文件                |
|                    | `edit_file`     | 编辑文件内容                |
|                    | `list_dir`      | 列出目录内容                |
| **网络能力** | `web_search`    | 联网搜索 (Tavily/Brave/DDG) |
|                    | `web_extract`   | 网页内容提取                |
| **记忆管理** | `remember`      | 主动存储记忆                |
|                    | `recall`        | 检索记忆                    |
|                    | `forget`        | 删除/归档记忆               |
| **系统控制** | `exec`          | 安全执行 Shell 命令         |
|                    | `session_title` | 管理会话标题                |

#### 网页搜索：三引擎降级设计

FinchBot 的网页搜索工具采用巧妙的**三引擎自动降级机制**，兼顾灵活性和开箱即用体验：

| 优先级 |          引擎          | API Key | 特点                             |
| :----: | :--------------------: | :-----: | :------------------------------- |
|   1   |    **Tavily**    |  需要  | 质量最佳，专为 AI 优化，深度搜索 |
|   2   | **Brave Search** |  需要  | 免费额度大，隐私友好             |
|   3   |  **DuckDuckGo**  |  无需  | 始终可用，零配置                 |

**工作原理**：

1. 如果设置了 `TAVILY_API_KEY` → 使用 Tavily（质量最佳）
2. 否则如果设置了 `BRAVE_API_KEY` → 使用 Brave Search
3. 否则 → 使用 DuckDuckGo（无需 API Key，始终可用）

这个设计确保**即使没有任何 API Key 配置，网页搜索也能开箱即用**！

#### 会话标题：智能命名，开箱即用

`session_title` 工具体现了 FinchBot 的开箱即用理念：

|       操作方式       | 说明                                   | 示例                   |
| :------------------: | :------------------------------------- | :--------------------- |
|  **自动生成**  | 对话 2-3 轮后，AI 自动根据内容生成标题 | "Python 异步编程讨论"  |
| **Agent 修改** | 告诉 Agent "把会话标题改成 XXX"        | Agent 调用工具自动修改 |
| **手动重命名** | 在会话管理器中按 `r` 键重命名        | 用户手动输入新标题     |

这个设计让用户**无需关心技术细节**，无论是自动还是手动，都能轻松管理会话。

### 4. 技能系统：用 Markdown 定义 Agent 能力

技能是 FinchBot 的独特创新——**用 Markdown 文件定义 Agent 的能力边界**。

#### 最大特色：Agent 自动创建技能

FinchBot 内置了 **skill-creator** 技能，这是开箱即用理念的极致体现：

> **只需告诉 Agent 你想要什么技能，Agent 就会自动创建好！**

```
用户: 帮我创建一个翻译技能，可以把中文翻译成英文

Agent: 好的，我来为你创建翻译技能...
       [调用 skill-creator 技能]
       ✅ 已创建 skills/translator/SKILL.md
       现在你可以直接使用翻译功能了！
```

无需手动创建文件、无需编写代码，**一句话就能扩展 Agent 能力**！

#### 技能文件结构

```
skills/
├── skill-creator/        # 技能创建器（内置）- 开箱即用的核心
│   └── SKILL.md
├── summarize/            # 智能总结（内置）
│   └── SKILL.md
├── weather/              # 天气查询（内置）
│   └── SKILL.md
└── my-custom-skill/      # Agent 自动创建或用户自定义
    └── SKILL.md
```

#### 核心设计亮点

|           特性           | 说明                              |
| :----------------------: | :-------------------------------- |
| **Agent 自动创建** | 告诉 Agent 需求，自动生成技能文件 |
|   **双层技能源**   | 工作区技能优先，内置技能兜底      |
|    **依赖检查**    | 自动检查 CLI 工具和环境变量       |
|  **缓存失效检测**  | 基于文件修改时间，智能缓存        |
|   **渐进式加载**   | 常驻技能优先，按需加载其他        |

### 5. LangChain 1.2 架构实践

FinchBot 基于 **LangChain v1.2** 和 **LangGraph v1.0** 构建，采用最新的 Agent 架构。

```python
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, SqliteSaver | MemorySaver]:
  
    # 1. 初始化检查点（持久化状态）
    if use_persistent:
        checkpointer = SqliteSaver.from_conn_string(str(db_path))
    else:
        checkpointer = MemorySaver()
  
    # 2. 构建系统提示
    system_prompt = build_system_prompt(workspace)
  
    # 3. 创建 Agent（使用 LangChain 官方 API）
    agent = create_agent(
        model=model,
        tools=list(tools) if tools else None,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )
  
    return agent, checkpointer
```

#### 支持的 LLM 提供商

|  提供商  | 模型                        | 特点             |
| :-------: | :-------------------------- | :--------------- |
|  OpenAI  | GPT-5, GPT-5.2, O3-mini     | 综合能力最强     |
| Anthropic | Claude Sonnet 4.5, Opus 4.6 | 安全性高，长文本 |
| DeepSeek | DeepSeek Chat, Reasoner     | 国产，性价比高   |
|  Gemini  | Gemini 2.5 Flash            | Google 最新      |
|   Groq   | Llama 4 Scout/Maverick      | 极速推理         |
| Moonshot | Kimi K1.5/K2.5              | 长文本，国产     |

---

## 快速开始

### 前置要求

|   项目   | 要求                    |
| :------: | :---------------------- |
| 操作系统 | Windows / Linux / macOS |
|  Python  | 3.13+                   |
| 包管理器 | uv (推荐)               |

### 安装步骤

```bash
# 克隆仓库（二选一）
# Gitee（国内推荐）
git clone https://gitee.com/xt765/finchbot.git
# 或 GitHub
git clone https://github.com/xt765/finchbot.git

cd finchbot

# 安装依赖
uv sync
```

> **注意**：嵌入模型（约 95MB）会在首次运行时（如运行 `finchbot chat`）自动下载到本地。无需手动干预。

<details>
<summary>开发环境安装</summary>

如需参与开发，安装开发依赖：

```bash
uv sync --extra dev
```

包含：pytest、ruff、basedpyright

</details>

### 最佳实践：三步上手

```bash
# 第一步：配置 API 密钥和默认模型
uv run finchbot config

# 第二步：管理你的会话
uv run finchbot sessions

# 第三步：开始对话
uv run finchbot chat
```

就这么简单！这三个命令覆盖了完整的工作流程：

- `finchbot config` — 交互式配置 LLM 提供商、API 密钥和设置
- `finchbot sessions` — 全屏会话管理器，创建、重命名、删除会话
- `finchbot chat` — 开始或继续交互式对话

### 备选方案：环境变量

```bash
# 或直接设置环境变量
export OPENAI_API_KEY="your-api-key"
uv run finchbot chat
```

### 日志级别控制

```bash
# 默认：显示 WARNING 及以上日志
finchbot chat

# 显示 INFO 及以上日志
finchbot -v chat

# 显示 DEBUG 及以上日志（调试模式）
finchbot -vv chat
```

### 可选：下载本地嵌入模型

```bash
# 用于记忆系统的语义搜索（可选但推荐）
uv run finchbot models download
```

### 创建自定义技能

```bash
# 创建技能目录
mkdir -p ~/.finchbot/workspace/skills/my-skill

# 创建技能文件
cat > ~/.finchbot/workspace/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: 我的自定义技能
metadata:
  finchbot:
    emoji: ✨
    always: false
---

# 我的自定义技能

当用户请求 XXX 时，我应该...
EOF
```

---

## 技术栈

|    层级    | 技术              |  版本  |
| :--------: | :---------------- | :-----: |
|  基础语言  | Python            |  3.13+  |
| Agent 框架 | LangChain         | 1.2.10+ |
|  状态管理  | LangGraph         | 1.0.8+ |
|  数据验证  | Pydantic          |   v2   |
|  向量存储  | ChromaDB          | 0.5.0+ |
|  本地嵌入  | FastEmbed         | 0.4.0+ |
|  搜索增强  | BM25              | 0.2.2+ |
|  CLI 框架  | Typer             | 0.23.0+ |
|   富文本   | Rich              | 14.3.0+ |
|    日志    | Loguru            | 0.7.3+ |
|  配置管理  | Pydantic Settings | 2.12.0+ |

---

## 扩展指南

### 添加新工具

继承 `FinchTool` 基类，实现 `_run()` 方法，然后注册到 `ToolRegistry`。

### 添加新技能

在 `~/.finchbot/workspace/skills/{skill-name}/` 下创建 `SKILL.md` 文件。

### 添加新的 LLM 提供商

在 `providers/factory.py` 中添加新的 Provider 类。

### 添加新语言

在 `i18n/locales/` 下添加新的 `.toml` 文件。

---

## 项目优势

|         优势         | 说明                                                        |
| :------------------: | :---------------------------------------------------------- |
|  **隐私优先**  | 使用 FastEmbed 本地生成向量，无需上传云端数据               |
|  **真持久化**  | 双层记忆存储架构，支持语义检索和精确查询                    |
| **生产级稳定** | 双重检查锁、自动重试、超时控制机制                          |
|  **灵活扩展**  | 继承 FinchTool 或创建 SKILL.md 即可扩展，无需修改核心代码   |
|  **模型无关**  | 支持 OpenAI, Anthropic, Gemini, DeepSeek, Moonshot, Groq 等 |
|  **并发安全**  | 工具注册使用双重检查锁定模式，线程安全                      |

---

## 文档

| 文档                                   | 说明          |
| :------------------------------------- | :------------ |
| [使用指南](docs/zh-CN/guide/usage.md)     | CLI 使用教程  |
| [API 接口文档](docs/zh-CN/api.md)         | API 参考      |
| [配置指南](docs/zh-CN/config.md)          | 配置项说明    |
| [扩展指南](docs/zh-CN/guide/extension.md) | 添加工具/技能 |
| [系统架构](docs/zh-CN/architecture.md)    | 系统架构详解  |
| [部署指南](docs/zh-CN/deployment.md)      | 部署说明      |
| [开发环境搭建](docs/zh-CN/development.md) | 开发环境配置  |
| [贡献指南](docs/zh-CN/contributing.md)    | 贡献规范      |

---

## 贡献

欢迎提交 Issue 和 Pull Request。请阅读 [贡献指南](docs/zh-CN/contributing.md) 了解更多信息。

---

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

## Star History

如果这个项目对你有帮助，请给个 Star ⭐️
