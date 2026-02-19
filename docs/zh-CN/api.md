# API 详细参考

本文档提供 FinchBot 核心类和方法的详细 API 参考。

## 1. Agent 模块 (`finchbot.agent`)

### 1.1 `create_finch_agent`

创建并配置一个 FinchBot 智能体实例。

```python
def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, SqliteSaver | MemorySaver]:
```

**参数**:
- `model`: 基础聊天模型实例 (如 `ChatOpenAI`, `ChatAnthropic`)。
- `workspace`: 工作目录路径 (`Path` 对象)，用于文件操作、记忆存储等。
- `tools`: 可用工具序列 (可选，默认为 None)。如果提供了工具，Agent 会自动绑定它们。
- `use_persistent`: 是否启用持久化存储 (Checkpointing)。默认为 `True`，启用后会保存对话历史到 SQLite。

**注意**: 系统提示词通过 `build_system_prompt(workspace)` 动态生成，而非通过参数传入。

**返回**:
- `(agent, checkpointer)` 元组:
    - `agent`: 编译后的 LangGraph 状态图，可调用 `.invoke()` 或 `.stream()`。
    - `checkpointer`: 持久化存储对象 (`SqliteSaver` 实例)。

**示例**:
```python
from pathlib import Path
from langchain_openai import ChatOpenAI
from finchbot.agent import create_finch_agent

model = ChatOpenAI(model="gpt-4")
workspace = Path("./workspace")
agent, checkpointer = create_finch_agent(model, workspace)

response = agent.invoke({"messages": [("user", "Hello!")]}, config={"configurable": {"thread_id": "1"}})
```

---

### 1.2 `ContextBuilder`

动态系统提示词构建器。

```python
class ContextBuilder:
    def __init__(self, workspace: Path): ...
    
    def build(self) -> str: ...
```

**方法**:
- `build()`: 生成完整的系统提示词字符串。它会组合：
    - `SYSTEM.md`: 基础角色设定。
    - `MEMORY_GUIDE.md`: 记忆使用准则。
    - `SKILL.md`: 动态加载的技能描述。
    - `TOOLS.md`: 自动生成的工具文档。
    - 运行时信息 (OS, Time, Python Version)。

---

## 2. Memory 模块 (`finchbot.memory`)

### 2.1 `MemoryManager`

记忆系统的统一入口。

```python
class MemoryManager:
    def __init__(self, workspace: Path, embedding_model: str = "BAAI/bge-small-zh-v1.5"): ...
```

#### `remember`

保存一条新记忆。

```python
def remember(
    self,
    content: str,
    category: str | None = None,
    importance: float | None = None,
    tags: list[str] | None = None,
) -> str:
```

**参数**:
- `content`: 记忆的文本内容。
- `category`: 分类 (可选，如 "personal", "work")。如果未提供，可能会自动推断。
- `importance`: 重要性评分 (0.0-1.0，可选)。如果未提供，可能会自动计算。
- `tags`: 标签列表 (可选)。

**返回**:
- `memory_id`: 新创建的记忆 ID (UUID)。

#### `recall`

检索相关记忆。

```python
def recall(
    self,
    query: str,
    top_k: int = 5,
    category: str | None = None,
    query_type: QueryType = QueryType.COMPLEX,
    similarity_threshold: float = 0.5,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
```

**参数**:
- `query`: 查询文本 (自然语言)。
- `top_k`: 返回结果数量 (默认 5)。
- `category`: 按分类过滤 (可选)。
- `query_type`: 查询类型 (默认 `QueryType.COMPLEX`)。
- `similarity_threshold`: 相似度阈值 (默认 0.5)。
- `include_archived`: 是否包含归档的记忆 (默认 False)。

**返回**:
- 记忆字典列表，每个包含 `id`, `content`, `category`, `importance`, `similarity` 等字段。

#### `forget`

删除或归档记忆。

```python
def forget(self, pattern: str) -> dict[str, Any]:
```

**参数**:
- `pattern`: 用于匹配记忆内容的字符串（支持通配符）。

**返回**:
- 删除统计信息字典，包含 `total_found`, `deleted`, `archived`, `pattern` 字段。

---

## 3. Tools 模块 (`finchbot.tools`)

所有工具均继承自 `finchbot.tools.base.FinchTool`。

### 3.1 `FinchTool` (基类)

```python
class FinchTool(BaseTool):
    name: str
    description: str
    parameters: dict
    
    def _run(self, *args, **kwargs) -> Any: ...
    async def _arun(self, *args, **kwargs) -> Any: ...
```

### 3.2 内置工具

| 工具类名 | 工具名称 (`name`) | 描述 | 关键参数 |
| :--- | :--- | :--- | :--- |
| `ReadFileTool` | `read_file` | 读取文件内容 | `file_path`: 文件路径 |
| `WriteFileTool` | `write_file` | 写入文件内容 | `file_path`: 路径, `content`: 内容 |
| `ListDirTool` | `list_dir` | 列出目录内容 | `dir_path`: 目录路径 |
| `ExecTool` | `exec_command` | 执行 Shell 命令 | `command`: 命令字符串 |
| `WebSearchTool` | `web_search` | 网络搜索 (Tavily) | `query`: 查询词 |
| `RememberTool` | `remember` | 写入记忆 | `content`: 内容 |
| `RecallTool` | `recall` | 检索记忆 | `query`: 查询词 |
| `ForgetTool` | `forget` | 删除记忆 | `pattern`: 匹配模式 |

---

## 4. Config 模块 (`finchbot.config`)

### 4.1 `Config` (根配置)

Pydantic 模型，定义整个应用的配置结构。

```python
class Config(BaseSettings):
    language: str = "en-US"
    language_set_by_user: bool = False
    default_model: str = "gpt-5"
    default_model_set_by_user: bool = False
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
```

### 4.2 `load_config`

加载配置。

```python
def load_config() -> Config: ...
```

**说明**:
- 自动合并默认配置、`~/.finchbot/config.json` 和环境变量。
- 环境变量优先级最高 (前缀 `FINCHBOT_`)。
