# 系统架构

本文档深入介绍 FinchBot 的系统架构、核心组件及其交互方式。

## 目录

1. [整体架构](#1-整体架构)
2. [核心组件](#2-核心组件)
   - [2.1 Agent 核心](#21-agent-核心)
   - [2.2 技能系统](#22-技能系统)
   - [2.3 记忆系统](#23-记忆系统)
   - [2.4 工具生态](#24-工具生态)
   - [2.5 通道系统](#25-通道系统)
   - [2.6 动态提示词系统](#26-动态提示词系统)
   - [2.7 I18n 系统](#27-i18n-系统国际化)
   - [2.8 配置系统](#28-配置系统)
   - [2.9 智能体自主性架构](#29-智能体自主性架构)
   - [2.10 后台任务系统](#210-后台任务系统-subagent)
   - [2.11 定时任务系统](#211-定时任务系统-cron)
   - [2.12 心跳服务](#212-心跳服务-heartbeat)
   - [2.13 MCP 自主配置](#213-mcp-自主配置)
   - [2.14 服务管理器](#214-服务管理器-servicemanager)
3. [数据流](#3-数据流)
4. [设计原则](#4-设计原则)
5. [扩展点](#5-扩展点)

---

## 1. 整体架构

FinchBot 基于 **LangChain v1.2** + **LangGraph v1.0** 构建，具备持久化记忆、动态工具调度、多平台消息支持和全异步并发启动能力。系统由四个核心组件构成：

1. **Agent 核心（大脑）**：负责决策、规划和工具调度，支持异步流式输出
2. **记忆系统**：负责长期信息存储和检索，采用 SQLite + FastEmbed + ChromaDB 混合架构
3. **工具生态**：负责与外部世界交互，支持延迟加载和线程池并发初始化，支持 MCP 协议
4. **通道系统**：负责多平台消息路由，支持 Discord、钉钉、飞书、微信、邮件等

### 1.1 整体架构图

```mermaid
flowchart TB
    classDef input fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#f57f17;
    classDef core fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef task fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;
    classDef infra fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    subgraph Input [输入层]
        direction LR
        CLI[CLI 界面<br/>Rich 美化]:::input
        LB[LangBot<br/>12+ 平台]:::input
        Webhook[Webhook<br/>FastAPI]:::input
    end

    subgraph Core [核心层 - Agent 决策引擎]
        direction TB
        Agent[LangGraph Agent<br/>状态管理 · 循环控制]:::core
        subgraph CoreModules [核心组件]
            direction LR
            Context[ContextBuilder<br/>上下文构建]:::core
            Streaming[ProgressReporter<br/>流式输出]:::core
        end
    end

    subgraph Capabilities [能力层 - 三层扩展]
        direction LR
        BuiltIn[内置工具<br/>19 个开箱即用]:::core
        MCP[MCP 扩展<br/>动态配置]:::core
        Skills[技能系统<br/>自主创建]:::core
    end

    subgraph Task [任务层 - 三层调度]
        direction LR
        BG[后台任务<br/>异步执行]:::task
        Cron[定时任务<br/>at/every/cron]:::task
        Heart[心跳监控<br/>自主唤醒]:::task
    end

    subgraph Memory [记忆层 - 双层存储]
        direction LR
        SQLite[(SQLite<br/>结构化存储)]:::infra
        Vector[(VectorStore<br/>向量检索)]:::infra
    end

    subgraph LLM [模型层 - 多提供商]
        direction LR
        OpenAI[OpenAI<br/>GPT-4o]:::infra
        Anthropic[Anthropic<br/>Claude]:::infra
        DeepSeek[DeepSeek<br/>国产]:::infra
    end

    CLI --> Agent
    LB <--> Webhook
    Webhook --> Agent

    Agent --> Context
    Agent --> Streaming
    Agent --> Capabilities
    Agent --> Task
    Agent <--> Memory
    Agent --> LLM

    Context --> Memory
    Memory --> SQLite
    Memory --> Vector
```

### 1.2 目录结构

```
finchbot/
├── agent/              # Agent 核心
│   ├── core.py        # Agent 创建与运行
│   ├── factory.py     # AgentFactory
│   ├── context.py     # ContextBuilder 提示词组装
│   ├── capabilities.py # CapabilitiesBuilder 能力构建
│   ├── capabilities_manager.py
│   ├── skills.py      # SkillsLoader Markdown 技能加载
│   ├── streaming.py   # ProgressReporter 进度流输出
│   ├── subagent.py    # SubagentManager 子代理管理
│   └── tools/         # Agent 专用工具
│       ├── background.py  # 后台任务工具
│       └── cron.py        # 定时任务工具
├── channels/           # 多平台消息（通过 LangBot）
│   ├── langbot.py     # LangBot 集成
│   ├── selector.py    # ChannelSelector
│   └── webhook_server.py  # Webhook 服务器（FastAPI）
├── cli/                # 命令行界面
│   ├── chat_session.py # 异步会话管理
│   ├── config_manager.py
│   ├── providers.py
│   └── ui.py
├── config/             # 配置管理
│   ├── loader.py
│   ├── schema.py      # 包含 MCPConfig, ChannelsConfig
│   ├── hot_reload.py  # 热重载
│   └── utils.py
├── constants.py        # 统一常量定义
├── cron/               # 定时任务系统
│   ├── service.py     # CronService 调度服务
│   ├── types.py       # 数据类定义
│   └── ui.py          # CronSelector 交互式 UI
├── heartbeat/          # 心跳服务
│   └── service.py     # HeartbeatService 后台服务
├── i18n/               # 国际化
│   ├── loader.py      # 语言加载器
│   └── locales/
├── memory/             # 记忆系统
│   ├── manager.py
│   ├── types.py
│   ├── services/       # 服务层
│   ├── storage/        # 存储层
│   └── vector_sync.py
├── providers/          # LLM 提供商
│   └── factory.py
├── services/           # 服务管理
│   ├── manager.py     # ServiceManager 统一管理
│   └── config.py      # ServiceConfig
├── sessions/           # 会话管理
│   ├── metadata.py
│   ├── selector.py
│   └── title_generator.py
├── skills/             # 技能系统
│   ├── skill-creator/
│   ├── summarize/
│   ├── task-management/
│   └── weather/
├── tools/              # 工具系统
│   ├── core.py        # ToolRegistry 单例注册表
│   ├── decorator.py   # @tool 装饰器
│   ├── middleware.py  # AgentMiddleware 中间件
│   ├── discovery.py   # 工具发现
│   ├── cache.py       # DynamicToolCache
│   ├── watcher.py     # 文件监控
│   ├── tools_generator.py  # 工具文档生成器
│   ├── builtin/       # 内置工具
│   │   ├── file.py    # 文件操作
│   │   ├── memory.py  # 记忆管理
│   │   ├── shell.py   # Shell 执行
│   │   ├── web.py     # 网络工具
│   │   ├── config.py  # 配置工具
│   │   ├── background.py  # 后台任务
│   │   ├── schedule.py    # 定时任务
│   │   └── session.py     # 会话管理
│   ├── mcp/           # MCP 工具
│   │   ├── connector.py   # MCPConnector
│   │   ├── wrapper.py     # MCPToolWithTimeout
│   │   └── hot_update.py  # 热更新管理
│   └── search/        # 搜索工具
│       ├── manager.py     # SearchManager
│       ├── tavily.py      # Tavily
│       ├── brave.py       # Brave
│       └── ddg.py         # DuckDuckGo
└── utils/              # 工具函数
    ├── cache.py
    ├── logger.py
    └── model_downloader.py
```

---

### 1.3 异步启动流程

FinchBot 引入了全异步启动架构，利用 `asyncio` 和 `concurrent.futures.ThreadPoolExecutor` 并发执行耗时操作，显著提升启动速度。

```mermaid
sequenceDiagram
    autonumber
    participant CLI as CLI（主线程）
    participant EventLoop as 事件循环
    participant Pool as 线程池
    participant LLM as LLM 初始化
    participant Mem as 记忆存储
    participant Tools as 工具工厂

    CLI->>EventLoop: 启动 _run_chat_session_async
    
    par 并发初始化任务
        EventLoop->>Pool: 提交 create_chat_model
        Pool->>LLM: 加载 Tiktoken/Schema（慢操作）
        LLM-->>Pool: 返回 ChatModel
        
        EventLoop->>Pool: 提交 SessionMetadataStore
        Pool->>Mem: 连接 SQLite
        Mem-->>Pool: 返回 Store
        
        EventLoop->>Pool: 提交 get_default_workspace
        Pool->>Pool: 文件 I/O 检查
    end
    
    EventLoop->>Pool: 提交 AgentFactory.create_for_cli
    Pool->>Tools: create_default_tools
    Tools-->>Pool: 返回工具列表
    Pool->>EventLoop: 返回 Agent 和工具
    
    EventLoop->>CLI: 初始化完成，进入交互循环
```

---

## 2. 核心组件

### 2.1 Agent 核心

**实现位置**：`src/finchbot/agent/`

Agent 核心是 FinchBot 的大脑，负责决策、规划和工具调度。现在使用工厂模式解耦创建逻辑。

#### 核心组件

* **AgentFactory（`factory.py`）**：负责组装 Agent，协调 ToolFactory 创建工具集，初始化 Checkpointer
* **Agent Core（`core.py`）**：负责 Agent 运行时逻辑
    * **状态管理**：基于 `LangGraph` 的 `StateGraph`，维护对话状态（`messages`）
    * **持久化**：使用 `SqliteSaver`（`checkpoints.db`）保存状态快照，支持恢复和历史回滚
* **ContextBuilder（`context.py`）**：动态组装系统提示词，包括：
    * **身份**：`SYSTEM.md`（角色定义）
    * **记忆指南**：`MEMORY_GUIDE.md`（记忆使用指南）
    * **灵魂**：`SOUL.md`（性格定义）
    * **技能**：动态加载的技能描述
    * **工具**：`TOOLS.md`（工具文档）
    * **能力**：`CAPABILITIES.md`（MCP 和能力信息）
    * **运行时信息**：当前时间、操作系统、Python 版本等

#### 关键类和函数

| 函数/类 | 说明 |
|:---|:---|
| `AgentFactory.create_for_cli()` | 静态工厂方法，为 CLI 创建配置好的 Agent |
| `create_finch_agent()` | 创建并配置 LangGraph Agent |
| `build_system_prompt()` | 构建完整的系统提示词 |
| `get_sqlite_checkpointer()` | 获取 SQLite 持久化检查点 |

#### 线程安全机制

工具注册使用**单锁模式**实现延迟加载，确保线程安全：

```python
def _ensure_tools_registered(
    workspace: Path | None = None,
    tools: Sequence[BaseTool] | None = None
) -> None:
    global _tools_registered

    with _tools_lock:
        if _tools_registered:
            return
        # 实际注册逻辑...
```

---

### 2.2 技能系统

**实现位置**：`src/finchbot/agent/skills.py`

技能是 FinchBot 的独特创新——**用 Markdown 文件定义 Agent 的能力边界**。

#### 最大特色：Agent 自动创建技能

FinchBot 内置了 **skill-creator** 技能，这是开箱即用理念的极致体现：

> **只需告诉 Agent 你想要什么技能，Agent 就会自动创建好！**

```
用户: 帮我创建一个翻译技能，可以把中文翻译成英文

Agent: 好的，我来为你创建翻译技能...
       [调用 skill-creator 技能]
       已创建 skills/translator/SKILL.md
       现在你可以直接使用翻译功能了！
```

无需手动创建文件、无需编写代码，**一句话就能扩展 Agent 能力**！

#### 技能文件结构

```yaml
# SKILL.md 示例
---
name: weather
description: 查询当前天气和预报（无需 API Key）
metadata:
  finchbot:
    emoji:
    always: false
    requires:
      bins: [curl]
      env: []
---
# 技能内容...
```

#### 核心设计模式

| 模式 | 说明 |
|:---:|:---|
| **双层技能源** | 工作区技能优先，内置技能兜底 |
| **依赖检查** | 自动检查 CLI 工具和环境变量 |
| **缓存失效检测** | 基于文件修改时间的智能缓存 |
| **渐进式加载** | 常驻技能优先，按需加载其他 |

---

### 2.3 记忆系统

**实现位置**：`src/finchbot/memory/`

FinchBot 实现了先进的**双层记忆架构**，彻底解决了 LLM 上下文窗口限制和长期记忆遗忘问题。

#### 为什么是 Agentic RAG？

| 维度 | 传统 RAG | Agentic RAG（FinchBot） |
|:---:|:---|:---|
| **检索触发** | 固定流程 | Agent 自主决策 |
| **检索策略** | 单一向量检索 | 混合检索 + 权重动态调整 |
| **记忆管理** | 被动存储 | 主动 remember/recall/forget |
| **分类能力** | 无 | 自动分类 + 重要性评分 |
| **更新机制** | 全量重建 | 增量同步 |

#### 双层存储架构

```mermaid
flowchart TB
    classDef businessLayer fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef serviceLayer fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef storageLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    MM[MemoryManager<br/>remember/recall/forget]:::businessLayer

    RS[RetrievalService<br/>混合检索 + RRF]:::serviceLayer
    CS[ClassificationService<br/>自动分类]:::serviceLayer
    IS[ImportanceScorer<br/>重要性评分]:::serviceLayer
    ES[EmbeddingService<br/>FastEmbed 本地]:::serviceLayer

    SQLite[(SQLiteStore<br/>真相源<br/>精确查询)]:::storageLayer
    Vector[(VectorStore<br/>ChromaDB<br/>语义检索)]:::storageLayer
    DS[DataSyncManager<br/>增量同步]:::storageLayer

    MM --> RS & CS & IS
    RS --> SQLite & Vector
    CS --> SQLite
    IS --> SQLite
    ES --> Vector
    
    SQLite <--> DS <--> Vector
```

#### 分层设计

1. **结构化层（SQLite）**：
    * **角色**：真相源（Source of Truth）
    * **内容**：全文、元数据（标签、来源）、分类、重要性评分、访问日志
    * **优势**：支持精确查询（如按时间、分类过滤）
    * **实现**：`SQLiteStore` 类，使用 `aiosqlite` 进行异步操作

2. **语义层（Vector Store）**：
    * **角色**：模糊检索和关联
    * **内容**：文本的 Embedding 向量
    * **技术栈**：ChromaDB + FastEmbed（本地轻量模型）
    * **优势**：支持自然语言语义搜索（如"上次提到的那本 Python 书"）
    * **实现**：`VectorMemoryStore` 类

#### 核心服务

| 服务 | 位置 | 功能 |
|:---|:---|:---|
| **DataSyncManager** | `memory/vector_sync.py` | 确保 SQLite 和 Vector Store 的最终一致性，支持重试 |
| **ImportanceScorer** | `memory/services/importance.py` | 自动评估记忆重要性（0.0-1.0），用于清理和优先级排序 |
| **RetrievalService** | `memory/services/retrieval.py` | 混合检索策略，结合向量相似度和元数据过滤 |
| **ClassificationService** | `memory/services/classification.py` | 基于关键词和语义的自动分类 |
| **EmbeddingService** | `memory/services/embedding.py` | 使用 FastEmbed 生成本地 Embedding |

#### 混合检索策略

FinchBot 采用**加权 RRF（Weighted Reciprocal Rank Fusion）**策略：

```python
class QueryType(StrEnum):
    """查询类型，决定检索权重"""
    KEYWORD_ONLY = "keyword_only"      # 纯关键词（1.0/0.0）
    SEMANTIC_ONLY = "semantic_only"    # 纯语义（0.0/1.0）
    FACTUAL = "factual"                # 事实型（0.8/0.2）
    CONCEPTUAL = "conceptual"          # 概念型（0.2/0.8）
    COMPLEX = "complex"                # 复杂型（0.5/0.5）
    AMBIGUOUS = "ambiguous"            # 歧义型（0.3/0.7）
```

#### MemoryManager 核心方法

```python
class MemoryManager:
    def remember(self, content: str, category=None, importance=None, ...)
    def recall(self, query: str, top_k=5, category=None, ...)
    def forget(self, pattern: str)
    def get_stats(self) -> dict
    def search_memories(self, ...)
    def get_recent_memories(self, days=7, limit=20)
    def get_important_memories(self, min_importance=0.8, limit=20)
```

---

### 2.4 工具生态

**实现位置**：`src/finchbot/tools/`

#### 装饰器注册机制

FinchBot 使用装饰器模式定义工具，自动注册到全局注册表：

* **@tool 装饰器**：将函数转换为 LangChain 工具并注册
* **@sync_tool 装饰器**：包装同步函数为异步工具
* **@class_tool 装饰器**：将类转换为工具

```python
@tool(
    name="read_file",
    description="读取文件内容",
    category=ToolCategory.FILE,
    requires_workspace=True,
)
async def read_file(file_path: str) -> str:
    ...
```

#### 工具元数据

每个工具都有 `ToolMeta` 元数据：

| 属性 | 说明 |
|:---|:---|
| `name` | 工具名称 |
| `description` | 工具描述 |
| `category` | 工具分类（ToolCategory 枚举） |
| `requires_workspace` | 是否需要工作区参数 |
| `requires_config` | 是否需要配置参数 |
| `dangerous` | 是否为危险工具 |
| `timeout` | 执行超时时间 |

#### 工具分类

```mermaid
flowchart TB
    subgraph 内置工具
        FILE["FILE<br/>read/write/edit/list"]
        MEMORY["MEMORY<br/>remember/recall/forget"]
        WEB["WEB<br/>search/extract"]
        SHELL["SHELL<br/>exec"]
        CONFIG["CONFIG<br/>configure_mcp/refresh"]
        BG["BACKGROUND<br/>start/check/cancel"]
        SCHED["SCHEDULE<br/>create/list/delete"]
    end
    
    subgraph MCP工具
        MCP["MCPConnector<br/>→ MCPToolWithTimeout"]
    end
    
    subgraph 注册表
        TR["ToolRegistry<br/>单例管理"]
    end
    
    内置工具 --> TR
    MCP --> TR
```

#### Middleware 层

基于 LangChain 1.0 AgentMiddleware API 实现：

```mermaid
flowchart LR
    TR["ToolRegistry"] --> MW["Middleware 层"]
    
    subgraph MW
        direction TB
        M1["DynamicToolMiddleware<br/>动态注入工具"]
        M2["ToolFilterMiddleware<br/>过滤可用工具"]
        M3["MCPHotUpdateMiddleware<br/>MCP 热更新"]
    end
    
    MW --> Agent["Agent"]
```

| Middleware | 功能 |
|:---|:---|
| `DynamicToolMiddleware` | 检查配置变化，动态注入 MCP 工具 |
| `ToolFilterMiddleware` | 根据配置过滤可用工具 |
| `MCPHotUpdateMiddleware` | MCP 配置变化时自动热更新 |

#### MCP 连接器

`MCPConnector` 管理 MCP 服务器的连接生命周期：

* **并发连接**：`connect_all()` 并发连接所有服务器
* **健康检查**：60 秒间隔检查服务器状态
* **重连机制**：最多 3 次重连尝试
* **超时控制**：`MCPToolWithTimeout` 包装工具

#### 安全沙箱

* **文件操作**：限制在工作区（`workspace`）内，防止越权访问系统文件
* **Shell 执行**：默认禁用高危命令（rm -rf /），并有超时控制

#### 内置工具一览

| 工具名称 | 类别 | 功能 |
|:---|:---|:---|
| `read_file` | FILE | 读取文件内容 |
| `write_file` | FILE | 写入文件 |
| `edit_file` | FILE | 编辑文件（行级别） |
| `list_dir` | FILE | 列出目录内容 |
| `exec` | SHELL | 执行 Shell 命令 |
| `web_search` | WEB | 网页搜索（Tavily/Brave/DuckDuckGo） |
| `web_extract` | WEB | 网页内容提取 |
| `remember` | MEMORY | 存储记忆 |
| `recall` | MEMORY | 检索记忆 |
| `forget` | MEMORY | 删除/归档记忆 |
| `configure_mcp` | CONFIG | 动态配置 MCP 服务器 |
| `refresh_capabilities` | CONFIG | 刷新能力描述文件 |
| `start_background_task` | BACKGROUND | 启动后台任务 |
| `check_task_status` | BACKGROUND | 检查任务状态 |
| `get_task_result` | BACKGROUND | 获取任务结果 |
| `cancel_task` | BACKGROUND | 取消任务 |
| `create_cron` | SCHEDULE | 创建定时任务 |
| `list_crons` | SCHEDULE | 列出定时任务 |
| `delete_cron` | SCHEDULE | 删除定时任务 |

#### 网页搜索：三引擎降级设计

```mermaid
flowchart TD
    classDef check fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef engine fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef fallback fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;

    Start[网页搜索请求]:::check
    
    Check1{TAVILY_API_KEY<br/>已设置?}:::check
    Tavily[Tavily<br/>质量最佳<br/>AI 优化]:::engine
    
    Check2{BRAVE_API_KEY<br/>已设置?}:::check
    Brave[Brave Search<br/>隐私友好<br/>免费额度大]:::engine
    
    DDG[DuckDuckGo<br/>零配置<br/>始终可用]:::fallback

    Start --> Check1
    Check1 -->|是| Tavily
    Check1 -->|否| Check2
    Check2 -->|是| Brave
    Check2 -->|否| DDG
```

| 优先级 | 引擎 | API Key | 特点 |
|:---:|:---:|:---:|:---|
| 1 | **Tavily** | 需要 | 质量最佳，专为 AI 优化，深度搜索 |
| 2 | **Brave Search** | 需要 | 免费额度大，隐私友好 |
| 3 | **DuckDuckGo** | 无需 | 始终可用，零配置 |

**工作原理**：

1. 如果设置了 `TAVILY_API_KEY` → 使用 Tavily（质量最佳）
2. 否则如果设置了 `BRAVE_API_KEY` → 使用 Brave Search
3. 否则 → 使用 DuckDuckGo（无需 API Key，始终可用）

这个设计确保**即使没有任何 API Key 配置，网页搜索也能开箱即用**！

#### 会话标题：智能命名，开箱即用

`session_title` 工具体现了 FinchBot 的开箱即用理念：

| 操作方式 | 说明 | 示例 |
|:---:|:---|:---|
| **自动生成** | 对话 2-3 轮后，AI 自动根据内容生成标题 | "Python 异步编程讨论" |
| **Agent 修改** | 告诉 Agent "把会话标题改成 XXX" | Agent 调用工具自动修改 |
| **手动重命名** | 在会话管理器中按 `r` 键重命名 | 用户手动输入新标题 |

这个设计让用户**无需关心技术细节**，无论是自动还是手动，都能轻松管理会话。

---

### 2.5 通道系统

**实现位置**：`src/finchbot/channels/`

通道系统已迁移到 [LangBot](https://github.com/langbot-app/LangBot) 平台，提供生产级的多平台消息支持。

#### 为什么选择 LangBot？

- **15k+ GitHub Stars**，活跃维护
- **支持 12+ 平台**：QQ、微信、企业微信、飞书、钉钉、Discord、Telegram、Slack、LINE、KOOK、Satori
- **内置 WebUI**：可视化配置各平台
- **插件生态**：支持 MCP 等扩展

#### LangBot 集成架构

```mermaid
flowchart LR
    classDef bus fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef manager fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef channel fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    FinchBot[FinchBot<br/>Agent 核心]:::bus
    LangBot[LangBot<br/>平台层]:::manager

    QQ[QQ]:::channel
    WeChat[微信]:::channel
    Feishu[飞书]:::channel
    DingTalk[钉钉]:::channel
    Discord[Discord]:::channel
    Telegram[Telegram]:::channel
    Slack[Slack]:::channel

    FinchBot <--> LangBot
    LangBot <--> QQ & WeChat & Feishu & DingTalk & Discord & Telegram & Slack
```

#### Webhook 服务器

**实现位置**：`src/finchbot/channels/webhook_server.py`

FinchBot 内置 FastAPI Webhook 服务器，用于接收 LangBot 的消息并返回 AI 响应。

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant P as 平台<br/>(QQ/微信等)
    participant L as LangBot
    participant W as Webhook<br/>FastAPI
    participant A as FinchBot<br/>Agent
    participant M as 记忆

    U->>P: 发送消息
    P->>L: 平台适配器
    L->>W: POST /webhook
    W->>W: 解析事件
    W->>A: 创建/获取 Agent
    A->>M: 召回上下文
    M-->>A: 返回记忆
    A->>A: LLM 推理
    A->>M: 存储新记忆
    A-->>W: 响应文本
    W-->>L: WebhookResponse
    L->>P: 发送回复
    P->>U: 显示响应
```

#### 快速开始

```bash
# 终端 1：启动 FinchBot Webhook 服务器
uv run finchbot webhook --port 8000

# 终端 2：启动 LangBot
uvx langbot

# 访问 LangBot WebUI http://localhost:5300
# 配置你的平台并设置 Webhook URL：
# http://localhost:8000/webhook
```

#### Webhook 配置

| 配置项 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `langbot_url` | LangBot API URL | `http://localhost:5300` |
| `langbot_api_key` | LangBot API Key | - |
| `langbot_webhook_path` | Webhook 端点路径 | `/webhook` |

更多详情请参阅 [LangBot 文档](https://docs.langbot.app)。

#### 核心组件（保留用于兼容性）

| 组件 | 文件 | 功能 |
|:---|:---|:---|
| **BaseChannel** | `base.py` | 抽象基类，定义通道接口（start, stop, send, receive） |
| **MessageBus** | `bus.py` | 异步消息路由器，管理入站/出站消息队列 |
| **ChannelManager** | `manager.py` | 协调多通道，处理消息路由和通道生命周期 |
| **InboundMessage** | `schema.py` | 标准化入站消息格式 |
| **OutboundMessage** | `schema.py` | 标准化出站消息格式 |

#### 消息模型

```python
class InboundMessage(BaseModel):
    """入站消息 - 从平台到 Agent"""
    channel_id: str          # 通道标识
    user_id: str             # 用户标识
    content: str             # 消息内容
    session_id: str | None   # 会话 ID
    metadata: dict = {}      # 附加元数据

class OutboundMessage(BaseModel):
    """出站消息 - 从 Agent 到平台"""
    channel_id: str          # 目标通道
    user_id: str             # 目标用户
    content: str             # 响应内容
    session_id: str | None   # 会话 ID
    metadata: dict = {}      # 附加元数据
```

---

### 2.6 动态提示词系统

**实现位置**：`src/finchbot/agent/context.py`

#### Bootstrap 文件系统

```
~/.finchbot/
├── config.json              # 主配置文件
└── workspace/
    ├── bootstrap/           # Bootstrap 文件目录
    │   ├── SYSTEM.md        # 角色定义
    │   ├── MEMORY_GUIDE.md  # 记忆使用指南
    │   ├── SOUL.md          # 性格设定
    │   └── AGENT_CONFIG.md  # Agent 配置
    ├── config/              # 配置目录
    │   └── mcp.json         # MCP 服务器配置
    ├── generated/           # 自动生成文件
    │   ├── TOOLS.md         # 工具文档
    │   └── CAPABILITIES.md  # 能力信息
    ├── skills/              # 自定义技能
    ├── memory/              # 记忆存储
    │   └── memory.db
    └── sessions/            # 会话存储
        └── checkpoints.db
```

#### 提示词加载流程

```mermaid
flowchart TD
    classDef startEnd fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef file fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef output fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    A([Agent 启动]):::startEnd --> B[加载 Bootstrap 文件]:::process
    
    B --> C[bootstrap/SYSTEM.md]:::file
    B --> D[bootstrap/MEMORY_GUIDE.md]:::file
    B --> E[bootstrap/SOUL.md]:::file
    B --> F[bootstrap/AGENT_CONFIG.md]:::file

    C --> G[组装提示词]:::process
    D --> G
    E --> G
    F --> G

    G --> H[加载常驻技能]:::process
    H --> I[构建技能摘要 XML]:::process
    I --> J[生成工具文档]:::process
    J --> K[注入运行时信息]:::process
    K --> L[完整系统提示]:::output

    L --> M([发送给 LLM]):::startEnd
```

---

### 2.7 I18n 系统（国际化）

**实现位置**：`src/finchbot/i18n/`

#### 支持的语言

- `zh-CN`：简体中文
- `en-US`：英语

#### 语言降级链

系统实现了智能降级机制：
```
zh-CN → zh → en-US
en-US →（无降级）
```

#### 配置优先级

1. 环境变量：`FINCHBOT_LANG`
2. 用户配置：`~/.finchbot/config.json`
3. 系统语言检测
4. 默认值：`en-US`

---

### 2.8 配置系统

**实现位置**：`src/finchbot/config/`

使用 Pydantic v2 + Pydantic Settings 进行类型安全的配置管理。

#### 配置结构

```
Config（根）
├── language
├── default_model
├── agents
│   └── defaults（Agent 默认值）
├── providers
│   ├── openai
│   ├── anthropic
│   ├── deepseek
│   ├── moonshot
│   ├── dashscope
│   ├── groq
│   ├── gemini
│   ├── openrouter
│   └── custom
├── tools
│   ├── web.search（搜索配置）
│   ├── exec（Shell 执行配置）
│   └── restrict_to_workspace
├── mcp                    # MCP 配置（存储在 workspace/config/mcp.json）
│   └── servers
│       └── {server_name}
│           ├── command    # stdio 传输命令
│           ├── args       # 命令参数
│           ├── env        # 环境变量
│           ├── url        # HTTP 传输 URL
│           ├── headers    # HTTP 请求头
│           └── disabled   # 是否禁用
└── channels               # 渠道配置（已迁移到 LangBot）
    ├── discord
    ├── feishu
    ├── dingtalk
    ├── wechat
    ├── email
    └── langbot_enabled
```

**工作区目录结构**：

```
workspace/
├── bootstrap/           # Bootstrap 文件（系统提示词）
├── config/              # 配置文件
│   └── mcp.json         # MCP 服务器配置
├── generated/           # 自动生成文件
│   ├── TOOLS.md         # 工具文档
│   └── CAPABILITIES.md  # 能力信息
├── skills/              # 技能目录
├── memory/              # 记忆存储
└── sessions/            # 会话数据
```

#### MCP 配置示例

```python
class MCPServerConfig(BaseModel):
    """单个 MCP 服务器配置
    
    支持 stdio 和 HTTP 两种传输方式。
    """
    command: str = ""           # stdio 传输的启动命令
    args: list[str] = []        # stdio 传输的命令参数
    env: dict[str, str] | None = None  # stdio 传输的环境变量
    url: str = ""               # HTTP 传输的服务器 URL
    headers: dict[str, str] | None = None  # HTTP 传输的请求头
    disabled: bool = False      # 是否禁用此服务器

class MCPConfig(BaseModel):
    """MCP 总配置
    
    使用 langchain-mcp-adapters 官方库加载 MCP 工具。
    """
    servers: dict[str, MCPServerConfig]
```

#### Channel 配置说明

渠道功能已迁移到 LangBot 平台。LangBot 支持 QQ、微信、飞书、钉钉、Discord、Telegram、Slack 等 12+ 平台。

请使用 LangBot 的 WebUI 配置各平台：https://langbot.app

此配置保留用于兼容性，后续版本将移除。

---

### 2.9 智能体自主性架构

**核心理念**: FinchBot 的设计目标是让智能体具备**真正的自主性**——不仅能响应用户请求，更能自主决策、自主执行、自主扩展。

#### 自主性金字塔

```mermaid
graph BT
    classDef level1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef level2 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef level3 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;
    classDef level4 fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#f57f17;

    L1[响应层<br/>响应用户请求]:::level1
    L2[执行层<br/>自主执行任务]:::level2
    L3[规划层<br/>自主设定计划]:::level3
    L4[扩展层<br/>自主扩展能力]:::level4

    L1 --> L2 --> L3 --> L4
```

| 层级 | 能力 | 实现机制 | 用户价值 |
|:---:|:---|:---|:---|
| **响应层** | 响应用户请求 | 对话系统 + 工具调用 | 基础交互 |
| **执行层** | 自主执行任务 | 后台任务系统 | 不阻塞对话 |
| **规划层** | 自主设定计划 | 定时任务 + 心跳服务 | 自动化执行 |
| **扩展层** | 自主扩展能力 | MCP 配置 + 技能创建 | 无限扩展 |

#### 自主性架构图

```mermaid
flowchart TB
    classDef core fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px,color:#4a148c;
    classDef auto fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef extend fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef callback fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    Agent[智能体<br/>自主决策中心]:::core

    subgraph Auto [自主执行能力]
        BG[后台任务<br/>SubagentManager<br/>独立 Agent 循环<br/>最多 15 次迭代]:::auto
        Cron[定时任务<br/>CronService<br/>at/every/cron 三种模式<br/>IANA 时区支持]:::auto
        Heartbeat[心跳服务<br/>自主监控与触发]:::auto
    end

    subgraph Callback [回调机制]
        OnNotify[on_notify<br/>后台任务结果通知]:::callback
        OnDeliver[on_deliver<br/>定时任务消息传递]:::callback
    end

    subgraph Extend [自我扩展能力]
        MCP[MCP 配置<br/>自主扩展工具能力<br/>超时控制/重连/健康检查]:::extend
        Skills[技能创建<br/>自主定义行为边界]:::extend
    end

    Agent --> Auto
    Agent --> Extend
    BG --> OnNotify
    Cron --> OnDeliver
    OnNotify --> Agent
    OnDeliver --> Agent
    MCP --> |新工具| Agent
```

#### 自主性对比

| 能力 | 传统 Agent | FinchBot 自主 Agent |
|:---|:---|:---|
| **任务执行** | 用户触发，阻塞等待 | 智能体自主启动后台任务 |
| **任务调度** | 用户手动设置 | 智能体自主创建定时任务 |
| **自我监控** | 无 | 心跳服务自主检查状态 |
| **能力扩展** | 开发者编写代码 | 智能体自主配置 MCP |
| **行为定义** | 硬编码提示词 | 智能体自主创建技能 |

---

### 2.10 后台任务系统 (Subagent)

**实现位置**：`src/finchbot/agent/subagent.py`、`src/finchbot/tools/builtin/background.py`

FinchBot 实现了先进的后台任务系统，采用**四工具模式**让 Agent 能够异步执行长时间任务。

#### 为什么需要后台任务？

| 场景 | 传统方式 | 后台任务方案 |
|:---:|:---|:---|
| **长时间研究** | 阻塞对话，用户等待 | 后台执行，继续对话 |
| **批量处理** | 超时失败 | 异步处理，状态追踪 |
| **代码生成** | 单线程阻塞 | 并发执行，提高效率 |

#### 四工具模式

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as 主 Agent
    participant SM as SubagentManager
    participant JM as JobManager
    participant SA as 子 Agent 循环

    U->>A: 执行长时间任务
    A->>SM: spawn(task, label, session_key)
    SM->>JM: 创建任务 (pending)
    SM->>SA: 创建独立 Agent 循环
    JM-->>A: 返回 job_id
    A-->>U: 任务已启动 (ID: xxx)
    
    Note over U,A: 用户继续对话...
    
    U->>A: 其他问题
    A-->>U: 正常响应
    
    U->>A: 任务进度如何？
    A->>SM: check_task_status
    SM->>JM: 查询状态
    JM-->>SM: running (迭代 5/15)
    A-->>U: 正在执行中...
    
    loop 最多 15 次迭代
        SA->>SA: 工具调用
        SA->>SA: LLM 推理
    end
    
    SA-->>SM: 任务完成
    SM->>SM: on_notify 回调
    SM->>A: 注入结果到会话
    A-->>U: 后台任务完成通知
```

#### 核心组件

| 组件 | 文件 | 功能 |
| :--- | :--- | :--- |
| **SubagentManager** | `agent/subagent.py` | 管理独立 Agent 循环，最多 15 次迭代 |
| **JobManager** | `tools/builtin/background.py` | 任务状态管理 |
| **BackgroundTools** | `tools/builtin/background.py` | 四个工具实现 |

#### SubagentManager 机制

SubagentManager 是后台任务的核心，实现了独立 Agent 循环执行：

| 特性 | 说明 |
| :--- | :--- |
| **独立 Agent 循环** | 创建独立的 Agent 实例执行任务 |
| **最大 15 次迭代** | 防止无限循环，确保任务终止 |
| **on_notify 回调** | 任务完成后通知主会话 |
| **会话级管理** | 每个会话独立的任务管理 |
| **工具绑定** | 预先绑定工具，避免序列化问题 |

#### 回调机制

```python
# CLI 中的回调实现
async def notify_result(session_key: str, label: str, result: str) -> None:
    """后台任务完成时注入结果到会话"""
    current_state = await agent.aget_state(config)
    messages = list(current_state.values.get("messages", []))
    messages.append(SystemMessage(content=f"[后台任务完成]\n{label}: {result}"))
    agent.update_state(config, {"messages": messages})
```

#### 任务状态流转

```mermaid
stateDiagram-v2
    [*] --> pending: start_background_task
    pending --> running: 任务开始执行
    running --> completed: 执行成功
    running --> failed: 执行失败
    running --> cancelled: cancel_task
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

#### 后台任务工具

| 工具 | 功能 | 智能体自主性 |
| :--- | :--- | :--- |
| `start_background_task` | 启动后台任务（独立 Agent 循环，最多 15 次迭代） | 智能体自主判断是否需要后台执行 |
| `check_task_status` | 检查任务状态 | 智能体自主决定何时检查 |
| `get_task_result` | 获取任务结果 | 智能体自主决定何时获取结果 |
| `cancel_task` | 取消任务 | 智能体自主决定是否取消 |

---

### 2.11 定时任务系统 (Cron)

**实现位置**：`src/finchbot/cron/`

FinchBot 提供了完整的定时任务解决方案，支持 **CLI 交互式管理** 和 **工具调用** 两种方式。

#### 三种调度模式

| 模式 | 参数 | 说明 | 使用场景 |
| :--- | :--- | :--- | :--- |
| **at** | `at="2025-01-15T10:30:00"` | 一次性任务，执行后自动删除 | 会议提醒、一次性通知 |
| **every** | `every_seconds=3600` | 间隔任务，每 N 秒执行一次 | 健康检查、定期同步 |
| **cron** | `cron_expr="0 9 * * *"` | Cron 表达式，精确时间调度 | 每日早报、工作日提醒 |

#### IANA 时区支持

支持 IANA 时区标识符，默认使用系统时区：

```python
create_cron(
    name="纽约股市开盘提醒",
    message="美股即将开盘",
    cron_expr="0 9:30 * * 1-5",
    tz="America/New_York"
)
```

#### 数据类定义

```mermaid
classDiagram
    class CronSchedule {
        +kind: str
        +at_ms: int
        +every_ms: int
        +expr: str
        +tz: str
        +validate()
    }
    
    class CronPayload {
        +kind: str
        +message: str
        +deliver: bool
        +channel: str
        +to: str
    }
    
    class CronJobState {
        +next_run_at_ms: int
        +last_run_at_ms: int
        +last_status: str
        +last_error: str
    }
    
    class CronJob {
        +id: str
        +name: str
        +enabled: bool
        +schedule: CronSchedule
        +payload: CronPayload
        +state: CronJobState
        +delete_after_run: bool
    }
    
    class CronStore {
        +version: str
        +jobs: List~CronJob~
    }
    
    CronJob --> CronSchedule
    CronJob --> CronPayload
    CronJob --> CronJobState
    CronStore --> CronJob
```

| 数据类 | 说明 |
| :--- | :--- |
| **CronSchedule** | 调度配置（at/every/cron 三种模式） |
| **CronPayload** | 任务内容（kind, message, deliver, channel, to） |
| **CronJobState** | 执行状态（下次/上次执行时间、状态、错误） |
| **CronJob** | 完整任务（整合 Schedule、Payload、State） |
| **CronStore** | 存储管理（JSON 持久化） |

#### 系统架构

```mermaid
flowchart TB
    subgraph CLI [CLI 交互]
        Command[finchbot cron]
        Selector[CronSelector]
    end

    subgraph Service [服务层]
        CronService[CronService<br/>croniter 调度引擎]
        TZ[IANA 时区支持]
    end

    subgraph Data [数据层]
        Store[(jobs.json)]
    end

    subgraph Tools [工具层]
        Create[create_cron]
        List[list_crons]
        Delete[delete_cron]
        Toggle[toggle_cron]
        RunNow[run_cron_now]
    end

    Command --> Selector --> CronService
    CronService --> TZ
    CronService --> Data
    
    Agent --> Tools --> Data
```

#### CronSelector 交互式界面

| 按键 | 操作 | 说明 |
|:---:|:---|:---|
| ↑ / ↓ | 导航 | 在任务列表中移动 |
| Enter | 详情 | 查看任务详细信息 |
| n | 新建 | 创建新的定时任务 |
| d | 删除 | 删除选中的任务 |
| e | 切换 | 启用/禁用任务 |
| r | 运行 | 立即执行一次 |
| q | 退出 | 退出管理界面 |

#### Cron 表达式支持

使用 `croniter` 库解析标准 5 字段 Cron 表达式：

| 表达式 | 说明 |
|:---|:---|
| `0 9 * * *` | 每天上午 9:00 |
| `0 */2 * * *` | 每 2 小时 |
| `30 18 * * 1-5` | 工作日下午 6:30 |
| `0 0 1 * *` | 每月 1 日零点 |

#### 定时任务工具

| 工具 | 功能 |
| :--- | :--- |
| `create_cron` | 创建定时任务（支持 at/every/cron） |
| `list_crons` | 列出所有任务 |
| `delete_cron` | 删除任务 |
| `toggle_cron` | 启用/禁用任务 |
| `run_cron_now` | 立即执行一次任务 |

---

### 2.12 心跳服务 (Heartbeat)

**实现位置**：`src/finchbot/heartbeat/`

心跳服务是 FinchBot 的后台监控服务，通过周期性读取 `HEARTBEAT.md` 文件来实现自动化任务触发。

#### 工作原理

```mermaid
sequenceDiagram
    participant S as HeartbeatService
    participant F as HEARTBEAT.md
    participant L as LLM
    participant A as 动作执行

    loop 每隔 N 秒
        S->>F: 读取文件内容
        F-->>S: 返回任务指令
        S->>L: 分析指令内容
        L-->>S: 决策执行动作
        alt 需要执行
            S->>A: 执行动作
            A-->>S: 返回结果
        end
    end
```

#### HEARTBEAT.md 文件格式

```markdown
# 心跳任务

## 待办事项
- [ ] 检查定时任务是否需要执行
- [ ] 检查后台任务状态
- [ ] 提醒用户重要事项

## 用户指令
- 每天 9 点提醒我查看邮件
- 当后台任务完成时通知我
```

#### 支持的动作类型

| 动作 | 说明 |
|:---|:---|
| `check_cron` | 检查并执行到期的定时任务 |
| `check_background` | 检查后台任务状态 |
| `remind_user` | 向用户发送提醒 |
| `custom_action` | 自定义动作 |

#### 与其他组件的集成

```mermaid
flowchart LR
    classDef heartbeat fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef cron fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef background fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;
    classDef notify fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    H[HeartbeatService]:::heartbeat
    C[CronService]:::cron
    B[BackgroundTasks]:::background
    N[通知系统]:::notify

    H --> |触发执行| C
    H --> |检查状态| B
    H --> |发送提醒| N
```

---

### 2.13 MCP 自主配置

**实现位置**：`src/finchbot/tools/mcp/`

**核心理念**: 让智能体能够自主配置 MCP 服务器，动态扩展自己的工具能力。

#### MCP 连接器架构

```mermaid
flowchart TB
    subgraph 配置层
        MCPConfig[mcp.json<br/>服务器配置]
    end
    
    subgraph 连接器
        Connect[connect_all<br/>并发连接]
        Health[健康检查<br/>60秒间隔]
        Reconnect[重连机制<br/>最多3次]
    end
    
    subgraph 工具包装
        Timeout[MCPToolWithTimeout<br/>超时控制]
    end
    
    subgraph 热更新
        Watcher[文件监控]
        Manager[热更新管理]
        Middleware[调用前检查]
    end
    
    MCPConfig --> 连接器
    连接器 --> 工具包装
    MCPConfig --> 热更新
    工具包装 --> Registry[ToolRegistry]
    Middleware --> Agent
```

#### MCPConnector 核心功能

| 功能 | 说明 |
|:---|:---|
| **并发连接** | `connect_all()` 并发连接所有服务器 |
| **健康检查** | 60 秒间隔检查服务器状态 |
| **重连机制** | 最多 3 次重连尝试 |
| **超时控制** | `MCPToolWithTimeout` 包装工具 |
| **资源管理** | `AsyncExitStack` 管理连接生命周期 |

#### 热更新机制

| 组件 | 功能 |
|:---|:---|
| `MCPHotUpdateManager` | 监控 mcp.json 变化，执行热更新 |
| `MCPHotUpdateMiddleware` | 在模型调用前检查并更新工具 |

#### 智能体自主扩展示例

```
用户：帮我分析这个 SQLite 数据库

智能体思考：
1. 当前工具检查：没有数据库操作工具
2. 能力缺口：需要 SQLite 操作能力
3. 解决方案：配置 SQLite MCP 服务器

智能体行动：
1. 调用 configure_mcp(
     action="add",
     server_name="sqlite",
     command="mcp-server-sqlite",
     args=["--db-path", "/path/to/db"]
   )
2. 调用 refresh_capabilities() 刷新能力描述
3. 新工具自动加载：query_sqlite, list_tables, ...

智能体使用新能力：
1. 调用 list_tables() 查看表结构
2. 调用 query_sqlite("SELECT * FROM users LIMIT 10")
3. 返回用户：数据库分析结果...
```

#### 支持的 MCP 操作

| 操作 | 功能 |
|:---|:---|
| `add` | 添加新服务器 |
| `update` | 更新配置 |
| `remove` | 删除服务器 |
| `enable` | 启用服务器 |
| `disable` | 禁用服务器 |
| `list` | 列出所有服务器 |

---

### 2.14 服务管理器 (ServiceManager)

**实现位置**：`src/finchbot/services/manager.py`

ServiceManager 是统一的后台服务管理器，负责协调所有后台服务的生命周期。

#### 服务架构

```mermaid
flowchart TB
    SM[ServiceManager<br/>统一服务管理器]

    subgraph Services [后台服务]
        Cron[CronService<br/>定时任务调度]
        Heart[HeartbeatService<br/>心跳监控]
        Sub[SubagentManager<br/>子代理管理]
        Job[JobManager<br/>任务状态管理]
    end

    subgraph Callbacks [回调机制]
        OnJob[on_job<br/>任务执行回调]
        OnDeliver[on_deliver<br/>消息投递回调]
        OnNotify[on_notify<br/>结果通知回调]
    end

    SM --> Services
    Cron --> OnJob
    Cron --> OnDeliver
    Sub --> OnNotify

    Registry[ToolRegistry<br/>共享工具注册表]
    SM --> Registry
```

#### 管理的服务

| 服务 | 功能 | 配置项 |
|:---|:---|:---|
| **CronService** | 定时任务调度 | `cron_enabled` |
| **HeartbeatService** | 心跳监控 | `heartbeat_enabled`, `heartbeat_interval_s` |
| **SubagentManager** | 子代理管理 | 自动启动 |
| **JobManager** | 任务状态管理 | 自动启动 |

#### 回调机制

| 回调 | 触发时机 | 用途 |
|:---|:---|:---|
| `on_job` | 定时任务执行时 | 执行任务逻辑 |
| `on_deliver` | 任务需要投递时 | 发送消息到指定渠道 |
| `on_notify` | 子代理完成时 | 通知主会话任务结果 |

#### 工具热更新

ServiceManager 支持工具热更新，当 MCP 配置变化时：

```python
async def update_tools(self, new_tools: list[BaseTool]) -> None:
    """更新所有服务的工具列表"""
    if "subagent_manager" in self._services:
        self._services["subagent_manager"].update_tools(new_tools)
    
    for callback in self._on_tool_update_callbacks:
        callback(new_tools)
```

#### 服务状态

```python
def get_status(self) -> dict[str, Any]:
    """获取服务状态"""
    return {
        "running": self._running,
        "services": {
            "cron": "cron" in self._services,
            "heartbeat": "heartbeat" in self._services,
            "subagent_manager": "subagent_manager" in self._services,
            "job_manager": "job_manager" in self._services,
        },
        "tool_count": self.registry.count(enabled_only=True),
    }
```

---

## 3. 数据流

### 3.1 完整数据流

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant C as 通道
    participant B as MessageBus
    participant F as AgentFactory
    participant A as Agent
    participant M as MemoryManager
    participant T as 工具
    participant L as LLM

    U->>C: 发送消息
    C->>B: InboundMessage
    B->>F: 获取/创建 Agent
    F->>A: 返回编译后的 Agent
    
    Note over A: 构建上下文
    A->>M: 召回相关记忆
    M-->>A: 返回上下文
    
    A->>L: 发送请求
    L-->>A: 流式响应
    
    alt 需要工具调用
        A->>T: 执行工具
        T-->>A: 返回结果
        A->>L: 继续处理
        L-->>A: 最终响应
    end
    
    A->>M: 存储新记忆
    A->>B: OutboundMessage
    B->>C: 路由到通道
    C->>U: 显示响应
```

### 3.2 对话流程

```mermaid
flowchart LR
    classDef startEnd fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    A[用户输入]:::startEnd --> B[CLI 接收]:::process
    B --> C[加载历史 Checkpoint]:::process
    C --> D[ContextBuilder 构建 Prompt]:::process
    D --> E[LLM 推理]:::process
    E --> F{需要工具?}:::decision
    F -->|否| G[生成最终响应]:::process
    F -->|是| H[执行工具]:::process
    H --> I[返回结果]:::process
    I --> E
    G --> J[保存 Checkpoint]:::process
    J --> K[显示给用户]:::startEnd
```

1. 用户输入 → CLI 接收
2. Agent 加载历史状态（Checkpoint）
3. ContextBuilder 构建当前 Prompt（包含相关记忆）
4. LLM 生成响应或工具调用请求
5. 如果工具调用 → 执行工具 → 返回结果给 LLM → 循环
6. LLM 生成最终响应 → 显示给用户

### 3.3 记忆写入流程（Remember）

1. Agent 调用 `remember` 工具
2. `MemoryManager` 接收内容
3. 自动计算 `category`（ClassificationService）
4. 自动计算 `importance`（ImportanceScorer）
5. 写入 SQLite，生成唯一 ID
6. 同步调用 Embedding 服务，写入向量到 ChromaDB
7. 记录访问日志

### 3.4 记忆检索流程（Recall）

1. Agent 调用 `recall` 工具（查询："我的 API Key 是什么"）
2. `RetrievalService` 将查询转为向量
3. 在 Vector Store 中搜索 Top-K 相似结果
4. （可选）结合 SQLite 进行元数据过滤（分类、时间范围等）
5. 返回结果给 Agent

---

## 4. 设计原则

### 4.1 模块化

每个组件都有清晰的职责边界：
- `MemoryManager` 不直接处理存储细节，委托给 `SQLiteStore` 和 `VectorMemoryStore`
- `ToolRegistry` 只处理注册和查找，不关心工具实现
- `I18n` 系统独立于业务逻辑
- `ChannelManager` 协调多通道，与 Agent 核心解耦

### 4.2 依赖倒置

高层模块不依赖低层模块，两者都依赖抽象：
```
AgentCore → MemoryManager（接口）
                ↓
         SQLiteStore / VectorStore（实现）
```

### 4.3 隐私优先

- Embedding 生成本地完成（FastEmbed），无需上传云端
- 配置文件存储在用户目录 `~/.finchbot`
- 文件操作限制在工作区内

### 4.4 开箱即用

FinchBot 将"开箱即用"作为核心设计原则：

| 特性 | 说明 |
|:---:|:---|
| **三步上手** | `config` → `sessions` → `chat`，三个命令完成工作流 |
| **环境变量** | 所有配置均可通过环境变量设置 |
| **Rich CLI 界面** | 全屏键盘导航，交互式操作 |
| **i18n 支持** | 内置中英文支持，自动检测系统语言 |
| **自动降级** | 网页搜索自动降级：Tavily → Brave → DuckDuckGo |
| **Agent 自动创建技能** | 告诉 Agent 需求，自动生成技能文件 |

### 4.5 防御性编程

- 单锁模式防止并发问题
- 向量存储失败不影响 SQLite 写入（降级策略）
- 超时控制防止工具挂起
- 完整的错误日志（Loguru）

---

## 5. 扩展点

### 5.1 添加新工具

继承 `FinchTool` 基类，实现 `_run()` 方法，然后注册到 `ToolRegistry`。

### 5.2 添加 MCP 工具

在配置文件中添加 MCP 服务器配置，支持 stdio 和 HTTP 传输。MCP 工具通过 `langchain-mcp-adapters` 自动加载。

### 5.3 添加新技能

在 `~/.finchbot/workspace/skills/{skill-name}/` 下创建 `SKILL.md` 文件。

### 5.4 添加新的 LLM 提供商

在 `providers/factory.py` 中添加新的 Provider 类。

### 5.5 多平台消息支持

使用 [LangBot](https://github.com/langbot-app/LangBot) 实现多平台支持。LangBot 支持 QQ、微信、飞书、钉钉、Discord、Telegram、Slack 等 12+ 平台。

详见 [LangBot 文档](https://docs.langbot.app)。

### 5.6 自定义记忆检索策略

继承 `RetrievalService` 或修改 `search()` 方法。

### 5.7 添加新语言

在 `i18n/locales/` 下添加新的 `.toml` 文件。

---

## 总结

FinchBot 的架构设计聚焦于：
- **可扩展性**：清晰的组件边界和接口
- **可靠性**：降级策略、重试机制、线程安全
- **可维护性**：类型安全、完整日志、模块化设计
- **隐私性**：敏感数据本地处理
- **多平台支持**：通过 LangBot 支持 QQ、微信、飞书、钉钉、Discord、Telegram、Slack 等 12+ 平台
- **MCP 支持**：通过官方 langchain-mcp-adapters 支持 stdio 和 HTTP 传输
