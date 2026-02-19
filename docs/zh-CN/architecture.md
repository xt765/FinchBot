# 系统架构详解

本文档深入介绍 FinchBot 的系统架构、核心组件及其交互方式。

## 1. 总体架构

FinchBot 采用 **LangChain** + **LangGraph** 构建，是一个具备持久化记忆和动态工具调度的 Agent 系统。系统主要由三个核心部分组成：

1.  **Agent Core (大脑)**: 负责决策、规划和工具调度。
2.  **Memory System (记忆)**: 负责长期信息的存储与检索。
3.  **Tool Ecosystem (工具)**: 负责与外部世界（文件系统、网络、命令行）交互。

```mermaid
graph TD
    User[用户] --> CLI[命令行界面]
    CLI --> Agent[Agent Core (LangGraph)]
    
    subgraph Core [Agent Core]
        Planner[规划器]
        Executor[执行器]
        Context[上下文构建器]
    end
    
    Agent --> Context
    Context --> SystemPrompt[系统提示词]
    
    Agent --> Memory[记忆系统]
    subgraph MemSys [Memory System]
        Manager[记忆管理器]
        SQLite[(SQLite 结构化存储)]
        Vector[(Vector 语义存储)]
        Sync[数据同步服务]
    end
    
    Manager --> SQLite
    Manager --> Vector
    SQLite <--> Sync <--> Vector
    
    Agent --> Tools[工具集]
    subgraph ToolSys [Tools]
        File[文件操作]
        Web[网络搜索]
        Shell[Shell 执行]
        Custom[自定义工具]
    end
```

## 2. 核心组件详解

### 2.1 Agent Core (智能体核心)

*   **实现位置**: `src/finchbot/agent/core.py`
*   **状态管理**: 基于 `LangGraph` 的 `StateGraph`，维护对话状态 (`messages`)。
*   **持久化**: 使用 `SqliteSaver` (`checkpoints.db`) 保存状态快照，支持断点续传和历史回溯。
*   **上下文构建 (`ContextBuilder`)**:
    *   动态组合系统提示词，包括：
        *   **Identity**: `SYSTEM.md` (角色设定)
        *   **Memory Guide**: `MEMORY_GUIDE.md` (记忆使用准则)
        *   **Skills**: 动态加载的技能描述
        *   **Tools**: `TOOLS.md` (工具文档)
        *   **Runtime Info**: 当前时间、操作系统、Python 版本等。

### 2.2 Memory System (记忆系统)

FinchBot 实现了先进的 **双层记忆架构**，旨在解决 LLM 上下文窗口限制和长期记忆遗忘问题。

*   **实现位置**: `src/finchbot/memory/`
*   **分层设计**:
    1.  **结构化层 (SQLite)**:
        *   **作用**: 事实来源 (Source of Truth)。
        *   **存储内容**: 完整文本、元数据 (tags, source)、分类 (category)、重要性评分 (importance)。
        *   **优势**: 支持精确查询（如按时间、分类过滤）。
    2.  **语义层 (Vector Store)**:
        *   **作用**: 模糊检索与联想。
        *   **存储内容**: 文本的 Embedding 向量。
        *   **技术栈**: ChromaDB + FastEmbed (本地轻量级模型)。
        *   **优势**: 支持自然语言语义搜索（如“上次我提到的那个Python库”）。

*   **核心服务**:
    *   **DataSyncManager**: 确保 SQLite 和 Vector Store 的数据最终一致性。
    *   **ImportanceScorer**: 自动评估记忆重要性 (0.0-1.0)，用于记忆清理和优先级排序。
    *   **RetrievalService**: 混合检索策略，结合向量相似度和元数据过滤。

### 2.3 Tool Ecosystem (工具生态)

*   **实现位置**: `src/finchbot/tools/`
*   **注册机制**:
    *   **ToolRegistry**: 单例注册表，管理所有可用工具。
    *   **Lazy Loading**: 默认工具（文件、搜索等）在 Agent 启动时自动注册。
*   **安全沙箱**:
    *   **文件操作**: 限制在工作区 (`workspace`) 内，防止越权访问系统文件。
    *   **Shell 执行**: 默认禁用高危命令 (rm -rf /)，支持超时控制。

## 3. 数据流向 (Data Flow)

### 3.1 对话流程
1.  用户输入 -> CLI 接收。
2.  Agent 加载历史状态 (Checkpoint)。
3.  ContextBuilder 构建当前 Prompt (包含相关记忆)。
4.  LLM 生成回复或工具调用请求。
5.  如果调用工具 -> 执行工具 -> 结果回传 LLM -> 循环。
6.  LLM 生成最终回复 -> 显示给用户。

### 3.2 记忆写入流程 (Remember)
1.  Agent 调用 `remember` 工具。
2.  `MemoryManager` 接收内容。
3.  自动计算 `category` 和 `importance`。
4.  写入 SQLite，生成唯一 ID。
5.  异步/同步调用 Embedding 服务，将向量写入 ChromaDB。

### 3.3 记忆检索流程 (Recall)
1.  Agent 调用 `recall` 工具 (查询: "我的API Key是多少")。
2.  `RetrievalService` 将查询转换为向量。
3.  在 Vector Store 中搜索 Top-K 相似结果。
4.  (可选) 结合 SQLite 进行元数据过滤。
5.  返回结果给 Agent。
