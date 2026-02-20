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
- `model`: 基础聊天模型实例 (如 `ChatOpenAI`, `ChatAnthropic`)
- `workspace`: 工作目录路径 (`Path` 对象)，用于文件操作、记忆存储等
- `tools`: 可用工具序列 (可选，默认为 None)。如果提供了工具，Agent 会自动绑定它们
- `use_persistent`: 是否启用持久化存储 (Checkpointing)。默认为 `True`，启用后会保存对话历史到 SQLite

**返回**:
- `(agent, checkpointer)` 元组:
    - `agent`: 编译后的 LangGraph 状态图，可调用 `.invoke()` 或 `.stream()`
    - `checkpointer`: 持久化存储对象 (`SqliteSaver` 实例)

**示例**:
```python
from pathlib import Path
from langchain_openai import ChatOpenAI
from finchbot.agent import create_finch_agent

model = ChatOpenAI(model="gpt-4")
workspace = Path("./workspace")
agent, checkpointer = create_finch_agent(model, workspace)

response = agent.invoke(
    {"messages": [("user", "Hello!")]}, 
    config={"configurable": {"thread_id": "1"}}
)
```

---

### 1.2 `ContextBuilder`

动态系统提示词构建器。

```python
class ContextBuilder:
    def __init__(self, workspace: Path): ...
    
    def build_system_prompt(self, skill_names, use_cache=True) -> str: ...
```

**方法**:
- `build_system_prompt()`: 生成完整的系统提示词字符串。它会组合：
    - `SYSTEM.md`: 基础角色设定
    - `MEMORY_GUIDE.md`: 记忆使用准则
    - `SKILL.md`: 动态加载的技能描述
    - `TOOLS.md`: 自动生成的工具文档
    - 运行时信息 (OS, Time, Python Version)

---

## 2. Memory 模块 (`finchbot.memory`)

### 2.1 `MemoryManager`

记忆系统的统一入口。

```python
class MemoryManager:
    def __init__(
        self, 
        workspace: Path, 
        embedding_model: str = "BAAI/bge-small-zh-v1.5"
    ): ...
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
- `content`: 记忆的文本内容
- `category`: 分类 (可选，如 "personal", "work")。如果未提供，会自动推断
- `importance`: 重要性评分 (0.0-1.0，可选)。如果未提供，会自动计算
- `tags`: 标签列表 (可选)

**返回**:
- `memory_id`: 新创建的记忆 ID (UUID)

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
- `query`: 查询文本 (自然语言)
- `top_k`: 返回结果数量 (默认 5)
- `category`: 按分类过滤 (可选)
- `query_type`: 查询类型 (默认 `QueryType.COMPLEX`)
    - `KEYWORD_ONLY`: 纯关键词检索 (1.0/0.0)
    - `SEMANTIC_ONLY`: 纯语义检索 (0.0/1.0)
    - `FACTUAL`: 事实型查询 (0.8/0.2)
    - `CONCEPTUAL`: 概念型查询 (0.2/0.8)
    - `COMPLEX`: 复杂型查询 (0.5/0.5)
    - `AMBIGUOUS`: 歧义型查询 (0.3/0.7)
- `similarity_threshold`: 相似度阈值 (默认 0.5)
- `include_archived`: 是否包含归档的记忆 (默认 False)

**返回**:
- 记忆字典列表，每个包含 `id`, `content`, `category`, `importance`, `similarity` 等字段

#### `forget`

删除或归档记忆。

```python
def forget(self, pattern: str) -> dict[str, Any]:
```

**参数**:
- `pattern`: 用于匹配记忆内容的字符串（支持部分匹配）

**返回**:
- 删除统计信息字典，包含 `total_found`, `deleted`, `archived`, `pattern` 字段

#### 使用示例

```python
from finchbot.memory import MemoryManager, QueryType
from pathlib import Path

# 初始化
manager = MemoryManager(Path.home() / ".finchbot" / "workspace")

# 保存记忆（自动分类 + 重要性评分）
memory = manager.remember(
    content="用户偏好使用深色主题，喜欢简洁的界面设计",
    category="preference",  # 可手动指定，也可自动推断
    importance=0.8
)

# 检索记忆 - 语义优先
results = manager.recall(
    query="用户界面偏好",
    query_type=QueryType.CONCEPTUAL,  # 概念型查询
    top_k=5
)

# 检索记忆 - 关键词优先
results = manager.recall(
    query="我的邮箱是多少",
    query_type=QueryType.FACTUAL,  # 事实型查询
    top_k=3
)

# 删除记忆
stats = manager.forget("旧邮箱")
```

---

## 3. Tools 模块 (`finchbot.tools`)

所有工具均继承自 `finchbot.tools.base.FinchTool`。

### 3.1 `FinchTool` (基类)

```python
class FinchTool(BaseTool):
    name: str
    description: str
    parameters: ClassVar[dict[str, Any]]
    
    def _run(self, *args, **kwargs) -> Any: ...
    async def _arun(self, *args, **kwargs) -> Any: ...
```

### 3.2 创建自定义工具

```python
from finchbot.tools.base import FinchTool
from typing import Any, ClassVar

class MyCustomTool(FinchTool):
    """自定义工具示例"""
    
    name: str = "my_custom_tool"
    description: str = "我的自定义工具描述"
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "input_text": {
                "type": "string",
                "description": "输入文本"
            }
        },
        "required": ["input_text"]
    }
    
    def _run(self, input_text: str) -> str:
        # 实现你的逻辑
        return f"处理结果: {input_text}"
```

### 3.3 内置工具

| 工具类名 | 工具名称 (`name`) | 描述 | 关键参数 |
|:---|:---|:---|:---|
| `ReadFileTool` | `read_file` | 读取文件内容 | `file_path`: 文件路径 |
| `WriteFileTool` | `write_file` | 写入文件内容 | `file_path`: 路径, `content`: 内容 |
| `EditFileTool` | `edit_file` | 编辑文件内容 | `file_path`: 路径, `old_text`: 旧文本, `new_text`: 新文本 |
| `ListDirTool` | `list_dir` | 列出目录内容 | `dir_path`: 目录路径 |
| `ExecTool` | `exec` | 执行 Shell 命令 | `command`: 命令字符串 |
| `WebSearchTool` | `web_search` | 网络搜索 | `query`: 查询词, `max_results`: 最大结果数 |
| `WebExtractTool` | `web_extract` | 提取网页内容 | `urls`: URL 列表 |
| `RememberTool` | `remember` | 写入记忆 | `content`: 内容, `category`: 分类 |
| `RecallTool` | `recall` | 检索记忆 | `query`: 查询词, `query_type`: 查询类型 |
| `ForgetTool` | `forget` | 删除记忆 | `pattern`: 匹配模式 |
| `SessionTitleTool` | `session_title` | 管理会话标题 | `action`: get/set, `title`: 标题 |

---

## 4. Skill 模块 (`finchbot.agent.skills`)

### 4.1 `SkillsLoader`

技能加载器。

```python
class SkillsLoader:
    def __init__(self, workspace: Path): ...
    
    def list_skills(self, use_cache: bool = True) -> list[dict]: ...
    def load_skill(self, name: str, use_cache: bool = True) -> str | None: ...
    def get_always_skills(self) -> list[str]: ...
    def build_skills_summary(self) -> str: ...
```

**方法**:
- `list_skills()`: 扫描并列出所有可用技能
- `load_skill()`: 加载指定技能内容
- `get_always_skills()`: 获取所有常驻技能（`always: true`）
- `build_skills_summary()`: 构建 XML 格式的技能摘要

---

## 5. Config 模块 (`finchbot.config`)

### 5.1 `Config` (根配置)

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

### 5.2 `load_config`

加载配置。

```python
def load_config() -> Config: ...
```

**说明**:
- 自动合并默认配置、`~/.finchbot/config.json` 和环境变量
- 环境变量优先级最高 (前缀 `FINCHBOT_`)

---

## 6. I18n 模块 (`finchbot.i18n`)

### 6.1 `I18nLoader`

国际化加载器。

```python
class I18nLoader:
    def __init__(self, locale: str = "en-US"): ...
    
    def get(self, key: str, default: str = "") -> str: ...
    def t(self, key: str, **kwargs) -> str: ...
```

**方法**:
- `get()`: 获取翻译文本
- `t()`: 获取翻译文本并支持变量替换

**示例**:
```python
from finchbot.i18n import I18nLoader

i18n = I18nLoader("zh-CN")

# 简单翻译
text = i18n.get("cli.help")

# 带变量的翻译
text = i18n.t("cli.chat.session", session_id="abc123")
```
