# 系统架构详解

本文档深入介绍 FinchBot 的系统架构、核心组件及其交互方式。

## 目录

1. [总体架构](#1-总体架构)
2. [核心组件详解](#2-核心组件详解)
3. [数据流向](#3-数据流向-data-flow)
4. [设计原则](#4-设计原则)
5. [扩展点](#5-扩展点)

---

## 1. 总体架构

FinchBot 采用 **LangChain v1.2** + **LangGraph v1.0** 构建，是一个具备持久化记忆和动态工具调度的 Agent 系统。系统主要由三个核心部分组成：

1. **Agent Core (大脑)**: 负责决策、规划和工具调度
2. **Memory System (记忆)**: 负责长期信息的存储与检索
3. **Tool Ecosystem (工具)**: 负责与外部世界（文件系统、网络、命令行）交互

```mermaid
graph TD
    User[用户] --> CLI[命令行界面]
    CLI --> Agent[Agent Core]

    subgraph Core
        Planner[规划器]
        Executor[执行器]
        ContextBuilder[上下文构建器]
        ConfigMgr[配置管理器]
    end

    Agent --> ContextBuilder
    ContextBuilder --> SystemPrompt[系统提示词]

    Agent --> MemoryMgr[记忆系统]
    subgraph MemSys
        Manager[记忆管理器]
        SQLite[(SQLite 存储)]
        Vector[(ChromaDB 向量)]
        Sync[数据同步]
        Classify[分类服务]
        Importance[重要性评分]
        Retrieval[检索服务]
    end

    Manager --> SQLite
    Manager --> Vector
    Manager --> Classify
    Manager --> Importance
    Manager --> Retrieval
    SQLite <--> Sync <--> Vector

    Agent --> ToolSet[工具集]
    subgraph ToolSys
        Registry[工具注册表]
        File[文件操作]
        Web[网络搜索]
        Shell[Shell 执行]
        Custom[自定义工具]
    end

    Registry --> File
    Registry --> Web
    Registry --> Shell
    Registry --> Custom

    Agent --> I18n[国际化]
```

### 1.1 目录结构

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

## 2. 核心组件详解

### 2.1 Agent Core (智能体核心)

**实现位置**: `src/finchbot/agent/core.py`

Agent Core 是 FinchBot 的大脑，负责决策、规划和工具调度。

#### 核心功能

* **状态管理**: 基于 `LangGraph` 的 `StateGraph`，维护对话状态 (`messages`)
* **持久化**: 使用 `SqliteSaver` (`checkpoints.db`) 保存状态快照，支持断点续传和历史回溯
* **上下文构建 (`ContextBuilder`)**: 动态组合系统提示词，包括：
    * **Identity**: `SYSTEM.md` (角色设定)
    * **Memory Guide**: `MEMORY_GUIDE.md` (记忆使用准则)
    * **Soul**: `SOUL.md` (灵魂设定)
    * **Skills**: 动态加载的技能描述
    * **Tools**: `TOOLS.md` (工具文档)
    * **Runtime Info**: 当前时间、操作系统、Python 版本等

#### 关键类与函数

| 函数/类 | 说明 |
|:---|:---|
| `create_finch_agent()` | 创建并配置 FinchBot Agent |
| `build_system_prompt()` | 构建完整的系统提示词 |
| `get_default_workspace()` | 获取默认工作目录 |
| `get_sqlite_checkpointer()` | 获取 SQLite 持久化检查点 |
| `get_memory_checkpointer()` | 获取内存检查点 |

#### 线程安全机制

工具注册采用 **双重检查锁定模式 (Double-checked locking)** 实现懒加载，确保线程安全：

```python
def _register_default_tools() -> None:
    global _default_tools_registered

    if _default_tools_registered:
        return

    with _tools_registration_lock:
        if _default_tools_registered:
            return
        # 实际注册逻辑...
```

---

### 2.2 技能系统 (Skills)

**实现位置**: `src/finchbot/agent/skills.py`

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

```yaml
# SKILL.md 示例
---
name: weather
description: 查询当前天气和天气预报（无需 API 密钥）
metadata:
  finchbot:
    emoji: 🌤️
    always: false
    requires:
      bins: [curl]
      env: []
---
# 技能正文...
```

#### 核心设计模式

| 模式 | 说明 |
|:---:|:---|
| **双层技能源** | 工作区技能优先，内置技能兜底 |
| **依赖检查** | 自动检查 CLI 工具和环境变量 |
| **缓存失效检测** | 基于文件修改时间，智能缓存 |
| **渐进式加载** | 常驻技能优先，按需加载其他 |

---

### 2.3 Memory System (记忆系统)

**实现位置**: `src/finchbot/memory/`

FinchBot 实现了先进的 **双层记忆架构**，旨在解决 LLM 上下文窗口限制和长期记忆遗忘问题。

#### 为什么是 Agentic RAG？

| 对比维度 | 传统 RAG | Agentic RAG (FinchBot) |
|:---:|:---|:---|
| **检索触发** | 固定流程 | Agent 自主决策 |
| **检索策略** | 单一向量检索 | 混合检索 + 权重动态调整 |
| **记忆管理** | 被动存储 | 主动 remember/recall/forget |
| **分类能力** | 无 | 自动分类 + 重要性评分 |
| **更新机制** | 全量重建 | 增量同步 |

#### 分层设计

1. **结构化层 (SQLite)**:
    * **作用**: 事实来源 (Source of Truth)
    * **存储内容**: 完整文本、元数据 (tags, source)、分类 (category)、重要性评分 (importance)、访问日志
    * **优势**: 支持精确查询（如按时间、分类过滤）
    * **实现**: `SQLiteStore` 类，使用 `aiosqlite` 异步操作

2. **语义层 (Vector Store)**:
    * **作用**: 模糊检索与联想
    * **存储内容**: 文本的 Embedding 向量
    * **技术栈**: ChromaDB + FastEmbed (本地轻量级模型)
    * **优势**: 支持自然语言语义搜索（如"上次我提到的那个Python库"）
    * **实现**: `VectorMemoryStore` 类

#### 核心服务

| 服务 | 位置 | 功能 |
|:---|:---|:---|
| **DataSyncManager** | `memory/vector_sync.py` | 确保 SQLite 和 Vector Store 的数据最终一致性，支持失败重试 |
| **ImportanceScorer** | `memory/services/importance.py` | 自动评估记忆重要性 (0.0-1.0)，用于记忆清理和优先级排序 |
| **RetrievalService** | `memory/services/retrieval.py` | 混合检索策略，结合向量相似度和元数据过滤 |
| **ClassificationService** | `memory/services/classification.py` | 基于关键词和语义的自动分类 |
| **EmbeddingService** | `memory/services/embedding.py` | 本地 Embedding 生成，使用 FastEmbed |

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

#### MemoryManager 接口

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

### 2.4 Tool Ecosystem (工具生态)

**实现位置**: `src/finchbot/tools/`

#### 注册机制

* **ToolRegistry**: 单例注册表，管理所有可用工具
* **Lazy Loading**: 默认工具（文件、搜索等）在 Agent 启动时自动注册
* **OpenAI 兼容**: 支持导出工具定义为 OpenAI Function Calling 格式

#### 工具基类

所有工具继承自 `FinchTool` 基类，必须实现：
- `name`: 工具名称
- `description`: 工具描述
- `parameters`: 参数定义 (JSON Schema)
- `_run()`: 执行逻辑

#### 安全沙箱

* **文件操作**: 限制在工作区 (`workspace`) 内，防止越权访问系统文件
* **Shell 执行**: 默认禁用高危命令 (rm -rf /)，支持超时控制

#### 内置工具列表

| 工具名 | 类别 | 文件 | 功能 |
|:---|:---|:---|:---|
| `read_file` | 文件 | `filesystem.py` | 读取文件内容 |
| `write_file` | 文件 | `filesystem.py` | 写入文件 |
| `edit_file` | 文件 | `filesystem.py` | 编辑文件（行级） |
| `list_dir` | 文件 | `filesystem.py` | 列出目录内容 |
| `exec` | 系统 | `shell.py` | 执行 Shell 命令 |
| `web_search` | 网络 | `web.py` / `search/` | 网页搜索（支持 Tavily/Brave/DDG） |
| `web_extract` | 网络 | `web.py` | 提取网页内容 |
| `remember` | 记忆 | `memory.py` | 存储记忆 |
| `recall` | 记忆 | `memory.py` | 检索记忆 |
| `forget` | 记忆 | `memory.py` | 删除/归档记忆 |
| `session_title` | 系统 | `session_title.py` | 管理会话标题 |

#### 网页搜索：三引擎降级设计

FinchBot 的网页搜索工具采用**三引擎自动降级机制**，兼顾灵活性和开箱即用体验：

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

### 2.5 动态提示词系统

**实现位置**: `src/finchbot/agent/context.py`

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

---

### 2.6 I18n 系统 (国际化)

**实现位置**: `src/finchbot/i18n/`

#### 支持的语言

- `zh-CN`: 简体中文
- `zh-HK`: 繁体中文
- `en-US`: 英文

#### 语言回退链

系统实现了智能回退机制：
```
zh-CN → zh → en-US
zh-HK → zh → en-US
en-US → (无回退)
```

#### 配置优先级

1. 环境变量: `FINCHBOT_LANG`
2. 用户配置: `~/.finchbot/config.json`
3. 系统语言检测
4. 默认: `en-US`

---

### 2.7 配置系统

**实现位置**: `src/finchbot/config/`

使用 Pydantic v2 + Pydantic Settings 实现类型安全的配置管理。

#### 配置结构

```
Config (根配置)
├── language
├── default_model
├── agents
│   └── defaults (Agent 默认配置)
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
└── tools
    ├── web.search (搜索配置)
    ├── exec (Shell 执行配置)
    └── restrict_to_workspace
```

---

## 3. 数据流向 (Data Flow)

### 3.1 对话流程

```mermaid
flowchart LR
    A[用户输入] --> B[CLI 接收]
    B --> C[加载历史 Checkpoint]
    C --> D[ContextBuilder 构建 Prompt]
    D --> E[LLM 推理]
    E --> F{需要工具?}
    F -->|否| G[生成最终回复]
    F -->|是| H[执行工具]
    H --> I[结果返回]
    I --> E
    G --> J[保存 Checkpoint]
    J --> K[显示给用户]
```

1. 用户输入 -> CLI 接收
2. Agent 加载历史状态 (Checkpoint)
3. ContextBuilder 构建当前 Prompt (包含相关记忆)
4. LLM 生成回复或工具调用请求
5. 如果调用工具 -> 执行工具 -> 结果回传 LLM -> 循环
6. LLM 生成最终回复 -> 显示给用户

### 3.2 记忆写入流程 (Remember)

1. Agent 调用 `remember` 工具
2. `MemoryManager` 接收内容
3. 自动计算 `category` (ClassificationService)
4. 自动计算 `importance` (ImportanceScorer)
5. 写入 SQLite，生成唯一 ID
6. 同步调用 Embedding 服务，将向量写入 ChromaDB
7. 记录访问日志

### 3.3 记忆检索流程 (Recall)

1. Agent 调用 `recall` 工具 (查询: "我的API Key是多少")
2. `RetrievalService` 将查询转换为向量
3. 在 Vector Store 中搜索 Top-K 相似结果
4. (可选) 结合 SQLite 进行元数据过滤 (category, time range 等)
5. 返回结果给 Agent

---

## 4. 设计原则

### 4.1 模块化 (Modularity)

每个组件都有清晰的职责边界：
- `MemoryManager` 不直接处理存储细节，委托给 `SQLiteStore` 和 `VectorMemoryStore`
- `ToolRegistry` 只负责注册和查找，不关心工具实现
- `I18n` 系统独立于业务逻辑

### 4.2 依赖倒置 (Dependency Inversion)

高层模块不依赖低层模块，都依赖抽象：
```
AgentCore → MemoryManager (接口)
                ↓
         SQLiteStore / VectorStore (实现)
```

### 4.3 隐私优先 (Privacy First)

- Embedding 生成在本地 (FastEmbed)，不上传云端
- 配置文件存储在用户目录 `~/.finchbot`
- 文件操作限制在工作区

### 4.4 开箱即用 (Out of the Box)

FinchBot 将"开箱即用"作为核心设计理念：

| 特性 | 说明 |
|:---:|:---|
| **三步上手** | `config` → `sessions` → `chat`，三个命令完成完整工作流程 |
| **环境变量配置** | 所有配置均可通过环境变量设置 |
| **Rich CLI 界面** | 全屏键盘导航，交互式操作 |
| **i18n 国际化** | 内置中英文支持，自动检测系统语言 |
| **自动降级** | 网页搜索自动降级：Tavily → Brave → DuckDuckGo |
| **Agent 自动创建技能** | 告诉 Agent 需求，自动生成技能文件 |

### 4.5 防御性编程 (Defensive Programming)

- 双重检查锁定防止并发问题
- 向量存储失败不影响 SQLite 写入（降级策略）
- 超时控制防止工具卡死
- 完整的错误日志 (Loguru)

---

## 5. 扩展点

### 5.1 添加新工具

继承 `FinchTool` 基类，实现 `_run()` 方法，然后注册到 `ToolRegistry`。

### 5.2 添加新技能

在 `~/.finchbot/workspace/skills/{skill-name}/` 下创建 `SKILL.md` 文件。

### 5.3 添加新的 LLM 提供商

在 `providers/factory.py` 中添加新的 Provider 类。

### 5.4 自定义记忆检索策略

继承 `RetrievalService` 或修改 `search()` 方法。

### 5.5 添加新语言

在 `i18n/locales/` 下添加新的 `.toml` 文件。

---

## 总结

FinchBot 的架构设计注重：
- **可扩展性**: 清晰的组件边界和接口
- **可靠性**: 降级策略、重试机制、线程安全
- **可维护性**: 类型安全、完善的日志、模块化设计
- **隐私性**: 本地处理敏感数据
