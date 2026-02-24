# API 详细参考

本文档提供 FinchBot 核心类和方法的详细 API 参考。

## 目录

1. [Agent 模块](#1-agent-模块-finchbotagent)
2. [Memory 模块](#2-memory-模块-finchbotmemory)
3. [Tools 模块](#3-tools-模块-finchbottools)
4. [Skill 模块](#4-skill-模块-finchbotagentskills)
5. [Channel 模块](#5-channel-模块-finchbotchannels)
6. [Config 模块](#6-config-模块-finchbotconfig)
7. [I18n 模块](#7-i18n-模块-finchboti18n)
8. [Providers 模块](#8-providers-模块-finchbotproviders)

---

## 1. Agent 模块 (`finchbot.agent`)

### 1.1 `AgentFactory`

Agent 工厂类，负责组装和配置 Agent 实例。

```python
class AgentFactory:
    @staticmethod
    def create_for_cli(
        model: BaseChatModel,
        workspace: Path,
        session_id: str,
        config: Config,
        session_metadata_store: SessionMetadataStore | None = None,
    ) -> tuple[CompiledStateGraph, SqliteSaver | MemorySaver, list[BaseTool]]:
```

**参数**:
- `model`: 基础聊天模型实例
- `workspace`: 工作目录路径
- `session_id`: 会话 ID
- `config`: 配置对象
- `session_metadata_store`: 会话元数据存储（可选）

**返回**:
- `(agent, checkpointer, tools)` 元组

---

### 1.2 `create_finch_agent`

创建并配置一个 FinchBot 智能体实例。

```python
async def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, AsyncSqliteSaver | MemorySaver]:
```

**参数**:
- `model`: 基础聊天模型实例 (如 `ChatOpenAI`, `ChatAnthropic`)
- `workspace`: 工作目录路径 (`Path` 对象)，用于文件操作、记忆存储等
- `tools`: 可用工具序列 (可选，默认为 None)
- `use_persistent`: 是否启用持久化存储 (Checkpointing)

**返回**:
- `(agent, checkpointer)` 元组:
    - `agent`: 编译后的 LangGraph 状态图
    - `checkpointer`: 持久化存储对象

**示例**:
```python
import asyncio
from pathlib import Path
from langchain_openai import ChatOpenAI
from finchbot.agent import create_finch_agent

async def main():
    model = ChatOpenAI(model="gpt-4")
    workspace = Path("./workspace")
    agent, checkpointer = await create_finch_agent(model, workspace)

    response = await agent.ainvoke(
        {"messages": [("user", "Hello!")]}, 
        config={"configurable": {"thread_id": "1"}}
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 1.3 `ContextBuilder`

动态系统提示词构建器。

```python
class ContextBuilder:
    def __init__(self, workspace: Path): ...
    
    def build_system_prompt(self, skill_names, use_cache=True) -> str: ...
```

**方法**:
- `build_system_prompt()`: 生成完整的系统提示词字符串

**提示词组成**:
- `SYSTEM.md`: 基础角色设定
- `MEMORY_GUIDE.md`: 记忆使用准则
- `SOUL.md`: 灵魂设定（性格特征）
- `AGENT_CONFIG.md`: Agent 配置
- `SKILL.md`: 动态加载的技能描述
- `TOOLS.md`: 自动生成的工具文档
- 运行时信息 (OS, Time, Python Version)

---

### 1.4 `get_sqlite_checkpointer`

获取 SQLite 持久化检查点。

```python
def get_sqlite_checkpointer(db_path: Path) -> SqliteSaver:
```

**参数**:
- `db_path`: SQLite 数据库文件路径

**返回**:
- `SqliteSaver` 实例

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
- `category`: 分类 (可选，如 "personal", "work")
- `importance`: 重要性评分 (0.0-1.0，可选)
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
- `similarity_threshold`: 相似度阈值 (默认 0.5)
- `include_archived`: 是否包含归档的记忆 (默认 False)

**QueryType 枚举**:

| 类型 | 描述 | 关键词权重 | 语义权重 |
|:---|:---|:---:|:---:|
| `KEYWORD_ONLY` | 纯关键词检索 | 1.0 | 0.0 |
| `SEMANTIC_ONLY` | 纯语义检索 | 0.0 | 1.0 |
| `FACTUAL` | 事实型查询 | 0.8 | 0.2 |
| `CONCEPTUAL` | 概念型查询 | 0.2 | 0.8 |
| `COMPLEX` | 复杂型查询 | 0.5 | 0.5 |
| `AMBIGUOUS` | 歧义型查询 | 0.3 | 0.7 |

**返回**:
- 记忆字典列表，每个包含 `id`, `content`, `category`, `importance`, `similarity` 等字段

#### `forget`

删除或归档记忆。

```python
def forget(self, pattern: str) -> dict[str, Any]:
```

**参数**:
- `pattern`: 用于匹配记忆内容的字符串

**返回**:
- 删除统计信息字典

#### 其他方法

```python
def get_stats(self) -> dict: ...
def search_memories(self, query: str, ...) -> list[dict]: ...
def get_recent_memories(self, days: int = 7, limit: int = 20) -> list[dict]: ...
def get_important_memories(self, min_importance: float = 0.8, limit: int = 20) -> list[dict]: ...
```

#### 使用示例

```python
from finchbot.memory import MemoryManager, QueryType
from pathlib import Path

manager = MemoryManager(Path.home() / ".finchbot" / "workspace")

memory = manager.remember(
    content="用户偏好使用深色主题",
    category="preference",
    importance=0.8
)

results = manager.recall(
    query="用户界面偏好",
    query_type=QueryType.CONCEPTUAL,
    top_k=5
)

stats = manager.forget("旧邮箱")
```

---

### 2.2 `QueryType`

查询类型枚举。

```python
class QueryType(StrEnum):
    KEYWORD_ONLY = "keyword_only"
    SEMANTIC_ONLY = "semantic_only"
    FACTUAL = "factual"
    CONCEPTUAL = "conceptual"
    COMPLEX = "complex"
    AMBIGUOUS = "ambiguous"
```

---

## 3. Tools 模块 (`finchbot.tools`)

### 3.1 `FinchTool` (基类)

所有工具的基类。

```python
class FinchTool(BaseTool):
    name: str
    description: str
    parameters: ClassVar[dict[str, Any]]
    
    def _run(self, *args, **kwargs) -> Any: ...
    async def _arun(self, *args, **kwargs) -> Any: ...
```

---

### 3.2 `ToolFactory`

工具工厂类。

```python
class ToolFactory:
    @staticmethod
    def create_default_tools(
        workspace: Path,
        config: Config,
        session_metadata_store: SessionMetadataStore | None = None,
    ) -> list[BaseTool]:
```

**参数**:
- `workspace`: 工作目录路径
- `config`: 配置对象
- `session_metadata_store`: 会话元数据存储（可选）

**返回**:
- 工具列表

---

### 3.3 `ToolRegistry`

工具注册表（单例模式）。

```python
class ToolRegistry:
    _instance: ClassVar[ToolRegistry | None] = None
    _tools: dict[str, BaseTool]
    
    @classmethod
    def get_instance(cls) -> ToolRegistry: ...
    
    def register(self, tool: BaseTool) -> None: ...
    def get(self, name: str) -> BaseTool | None: ...
    def list_tools(self) -> list[str]: ...
    def get_all_tools(self) -> list[BaseTool]: ...
```

---

### 3.4 创建自定义工具

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
        return f"处理结果: {input_text}"
```

---

### 3.5 内置工具

| 工具类名 | 工具名称 | 描述 | 关键参数 |
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
- `get_always_skills()`: 获取所有常驻技能
- `build_skills_summary()`: 构建 XML 格式的技能摘要

---

### 4.2 技能文件格式

```yaml
---
name: skill-name
description: 技能描述
metadata:
  finchbot:
    emoji: ✨
    always: false
    requires:
      bins: [curl, jq]
      env: [API_KEY]
---
# 技能正文 (Markdown)
```

---

## 5. Channel 模块 (`finchbot.channels`)

### 5.1 `BaseChannel`

通道抽象基类。

```python
class BaseChannel(ABC):
    @abstractmethod
    async def start(self) -> None: ...
    
    @abstractmethod
    async def stop(self) -> None: ...
    
    @abstractmethod
    async def send(self, message: OutboundMessage) -> None: ...
    
    @abstractmethod
    async def receive(self) -> AsyncGenerator[InboundMessage, None]: ...
```

---

### 5.2 `MessageBus`

异步消息路由器。

```python
class MessageBus:
    def __init__(self): ...
    
    @property
    def inbound(self) -> asyncio.Queue[InboundMessage]: ...
    
    @property
    def outbound(self) -> asyncio.Queue[OutboundMessage]: ...
    
    async def publish_inbound(self, message: InboundMessage) -> None: ...
    async def publish_outbound(self, message: OutboundMessage) -> None: ...
    async def consume_inbound(self) -> AsyncGenerator[InboundMessage, None]: ...
    async def consume_outbound(self) -> AsyncGenerator[OutboundMessage, None]: ...
```

---

### 5.3 `ChannelManager`

通道管理器。

```python
class ChannelManager:
    def __init__(self, bus: MessageBus): ...
    
    def register_channel(self, channel: BaseChannel) -> None: ...
    def unregister_channel(self, channel_id: str) -> None: ...
    async def start_all(self) -> None: ...
    async def stop_all(self) -> None: ...
```

---

### 5.4 消息模型

```python
class InboundMessage(BaseModel):
    """入站消息"""
    channel_id: str
    user_id: str
    content: str
    session_id: str | None = None
    metadata: dict = {}

class OutboundMessage(BaseModel):
    """出站消息"""
    channel_id: str
    user_id: str
    content: str
    session_id: str | None = None
    metadata: dict = {}
```

---

## 6. Config 模块 (`finchbot.config`)

### 6.1 `Config` (根配置)

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

---

### 6.2 `load_config`

加载配置。

```python
def load_config() -> Config: ...
```

**说明**:
- 自动合并默认配置、`~/.finchbot/config.json` 和环境变量
- 环境变量优先级最高 (前缀 `FINCHBOT_`)

---

### 6.3 配置结构

```
Config (根配置)
├── language
├── default_model
├── agents
│   └── defaults
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
    ├── web.search
    ├── exec
    └── restrict_to_workspace
```

---

## 7. I18n 模块 (`finchbot.i18n`)

### 7.1 `I18nLoader`

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

text = i18n.get("cli.help")
text = i18n.t("cli.chat.session", session_id="abc123")
```

---

### 7.2 支持的语言

| 语言代码 | 语言名称 |
|:---|:---|
| `zh-CN` | 简体中文 |
| `zh-HK` | 繁体中文 |
| `en-US` | 英文 |

---

## 8. Providers 模块 (`finchbot.providers`)

### 8.1 `create_chat_model`

创建聊天模型。

```python
def create_chat_model(
    provider: str,
    model: str,
    config: Config,
) -> BaseChatModel:
```

**参数**:
- `provider`: 提供商名称
- `model`: 模型名称
- `config`: 配置对象

**返回**:
- `BaseChatModel` 实例

---

### 8.2 支持的提供商

| 提供商 | 模型示例 | 环境变量 |
|:---|:---|:---|
| OpenAI | gpt-5, gpt-5.2, o3-mini | `OPENAI_API_KEY` |
| Anthropic | claude-sonnet-4.5, claude-opus-4.6 | `ANTHROPIC_API_KEY` |
| DeepSeek | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` |
| Gemini | gemini-2.5-flash | `GOOGLE_API_KEY` |
| Groq | llama-4-scout, llama-4-maverick | `GROQ_API_KEY` |
| Moonshot | kimi-k1.5, kimi-k2.5 | `MOONSHOT_API_KEY` |
| OpenRouter | (多种模型) | `OPENROUTER_API_KEY` |

---

### 8.3 使用示例

```python
from finchbot.providers import create_chat_model
from finchbot.config import load_config

config = load_config()

model = create_chat_model(
    provider="openai",
    model="gpt-5",
    config=config,
)
```
