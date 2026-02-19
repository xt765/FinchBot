# API 参考文档

## 核心模块

### 1. Agent (`finchbot.agent`)

FinchBot 的智能体核心，基于 LangGraph 构建。

- **`create_finch_agent(model, workspace, ...)`**: 创建并配置 Agent 实例。
- **`ContextBuilder`**: 动态构建系统提示词，管理 System Prompt、Memory Guide 和 Skills。

### 2. Memory (`finchbot.memory`)

分层记忆系统，负责管理短期和长期记忆。

- **`MemoryManager`**: 记忆系统的统一入口。
    - `remember(content, ...)`: 保存新记忆。
    - `recall(query, ...)`: 检索相关记忆。
    - `forget(pattern)`: 删除或归档记忆。
- **`SQLiteStore`**: 基于 SQLite 的结构化存储。
- **`VectorMemoryStore`**: 基于 ChromaDB/FastEmbed 的向量存储。

### 3. Tools (`finchbot.tools`)

工具生态系统。

- **`ToolRegistry`**: 工具注册表，管理所有可用工具。
- **`BaseTool`**: 所有工具的基类。
- **内置工具**:
    - `ReadFileTool`: 读取文件内容。
    - `WriteFileTool`: 写入文件。
    - `WebSearchTool`: 网络搜索 (DuckDuckGo/Tavily)。
    - `ExecTool`: 安全执行 Shell 命令。

## 辅助模块

### Configuration (`finchbot.config`)

- **`Config`**: Pydantic 模型，定义配置结构。
- **`load_config()`**: 加载并合并配置（文件 + 环境变量）。

### I18n (`finchbot.i18n`)

- **`t(key, **kwargs)`**: 获取翻译文本。
- **`I18n`**: 国际化加载器。
