# API 参考

本文档提供 FinchBot 核心类和方法的详细 API 参考。

## 目录

1. [Agent 模块](#1-agent-模块finchbotagent)
2. [记忆模块](#2-记忆模块finchbotmemory)
3. [工具模块](#3-工具模块finchbottools)
4. [技能模块](#4-技能模块finchbotagentskills)
5. [通道模块](#5-通道模块finchbotchannels)
6. [配置模块](#6-配置模块finchbotconfig)
7. [国际化模块](#7-国际化模块finchboti18n)
8. [提供商模块](#8-提供商模块finchbotproviders)
9. [MCP 模块](#9-mcp-模块finchbotmcp)

---

## 1. Agent 模块 (`finchbot.agent`)

### 1.1 `AgentFactory`

用于组装和配置 Agent 实例的工厂类。

```python
class AgentFactory:
    @staticmethod
    async def create_for_cli(
        session_id: str,
        workspace: Path,
        model: BaseChatModel,
        config: Config,
    ) -> tuple[CompiledStateGraph, Any, list[Any]]:
```

**参数**：
- `session_id`：会话 ID
- `workspace`：工作区目录路径
- `model`：基础聊天模型实例
- `config`：配置对象

**返回值**：
- `(agent, checkpointer, tools)` 元组

---

### 1.2 `create_finch_agent`

创建并配置 FinchBot Agent 实例。

```python
async def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, AsyncSqliteSaver | MemorySaver]:
```

**参数**：
- `model`：基础聊天模型实例（如 `ChatOpenAI`、`ChatAnthropic`）
- `workspace`：工作区目录路径（`Path` 对象）
- `tools`：可用工具序列（可选，默认为 None）
- `use_persistent`：是否启用持久化存储（检查点）

**返回值**：
- `(agent, checkpointer)` 元组：
    - `agent`：编译后的 LangGraph 状态图
    - `checkpointer`：持久化存储对象

**示例**：
```python
import asyncio
from pathlib import Path
from langchain_openai import ChatOpenAI
from finchbot.agent import create_finch_agent

async def main():
    model = ChatOpenAI(model="gpt-5")
    workspace = Path("./workspace")
    agent, checkpointer = await create_finch_agent(model, workspace)

    response = await agent.ainvoke(
        {"messages": [("user", "你好！")]}, 
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

**方法**：
- `build_system_prompt()`：生成完整的系统提示词字符串

**提示词组件**：
- `SYSTEM.md`：基础角色定义
- `MEMORY_GUIDE.md`：记忆使用指南
- `SOUL.md`：灵魂定义（性格）
- `AGENT_CONFIG.md`：Agent 配置
- `SKILL.md`：动态加载的技能描述
- `TOOLS.md`：自动生成的工具文档
- `CAPABILITIES.md`：自动生成的 MCP 和能力信息
- 运行时信息（操作系统、时间、Python 版本）

---

### 1.4 `get_sqlite_checkpointer`

获取 SQLite 持久化检查点。

```python
def get_sqlite_checkpointer(db_path: Path) -> SqliteSaver:
```

**参数**：
- `db_path`：SQLite 数据库文件路径

**返回值**：
- `SqliteSaver` 实例

---

## 2. 记忆模块 (`finchbot.memory`)

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

保存新记忆。

```python
def remember(
    self,
    content: str,
    category: str | None = None,
    importance: float | None = None,
    tags: list[str] | None = None,
) -> str:
```

**参数**：
- `content`：记忆文本内容
- `category`：分类（可选，如 "personal"、"work"）
- `importance`：重要性评分（0.0-1.0，可选）
- `tags`：标签列表（可选）

**返回值**：
- `memory_id`：新创建的记忆 ID（UUID）

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

**参数**：
- `query`：查询文本（自然语言）
- `top_k`：返回结果数量（默认 5）
- `category`：按分类过滤（可选）
- `query_type`：查询类型（默认 `QueryType.COMPLEX`）
- `similarity_threshold`：相似度阈值（默认 0.5）
- `include_archived`：是否包含已归档记忆（默认 False）

**QueryType 枚举**：

| 类型 | 说明 | 关键词权重 | 语义权重 |
|:---|:---|:---:|:---:|
| `KEYWORD_ONLY` | 纯关键词检索 | 1.0 | 0.0 |
| `SEMANTIC_ONLY` | 纯语义检索 | 0.0 | 1.0 |
| `FACTUAL` | 事实型查询 | 0.8 | 0.2 |
| `CONCEPTUAL` | 概念型查询 | 0.2 | 0.8 |
| `COMPLEX` | 复杂查询 | 0.5 | 0.5 |
| `AMBIGUOUS` | 歧义查询 | 0.3 | 0.7 |

**返回值**：
- 记忆字典列表，每个包含 `id`、`content`、`category`、`importance`、`similarity` 等

#### `forget`

删除或归档记忆。

```python
def forget(self, pattern: str) -> dict[str, Any]:
```

**参数**：
- `pattern`：匹配记忆内容的字符串

**返回值**：
- 删除统计字典

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
    content="用户偏好深色主题",
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

## 3. 工具模块 (`finchbot.tools`)

### 3.1 `FinchTool`（基类）

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

**参数**：
- `workspace`：工作区目录路径
- `config`：配置对象
- `session_metadata_store`：会话元数据存储（可选）

**返回值**：
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
    """自定义工具示例。"""
    
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
        return f"结果: {input_text}"
```

---

### 3.5 内置工具

| 工具类 | 工具名称 | 说明 | 关键参数 |
|:---|:---|:---|:---|
| `ReadFileTool` | `read_file` | 读取文件内容 | `file_path`：文件路径 |
| `WriteFileTool` | `write_file` | 写入文件内容 | `file_path`：路径，`content`：内容 |
| `EditFileTool` | `edit_file` | 编辑文件内容 | `file_path`：路径，`old_text`：旧文本，`new_text`：新文本 |
| `ListDirTool` | `list_dir` | 列出目录内容 | `dir_path`：目录路径 |
| `ExecTool` | `exec` | 执行 Shell 命令 | `command`：命令字符串 |
| `WebSearchTool` | `web_search` | 网页搜索 | `query`：查询，`max_results`：最大结果数 |
| `WebExtractTool` | `web_extract` | 提取网页内容 | `urls`：URL 列表 |
| `RememberTool` | `remember` | 保存记忆 | `content`：内容，`category`：分类 |
| `RecallTool` | `recall` | 检索记忆 | `query`：查询，`query_type`：查询类型 |
| `ForgetTool` | `forget` | 删除记忆 | `pattern`：匹配模式 |
| `SessionTitleTool` | `session_title` | 管理会话标题 | `action`：get/set，`title`：标题 |
| `ConfigureMCPTool` | `configure_mcp` | 动态配置 MCP 服务器 | `action`, `server_name`, `command`, `args`, `env`, `url` |
| `RefreshCapabilitiesTool` | `refresh_capabilities` | 刷新能力描述文件 | 无 |
| `GetCapabilitiesTool` | `get_capabilities` | 获取当前能力描述 | 无 |
| `GetMCPConfigPathTool` | `get_mcp_config_path` | 获取 MCP 配置文件路径 | 无 |

---

## 4. 技能模块 (`finchbot.agent.skills`)

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

**方法**：
- `list_skills()`：扫描并列出所有可用技能
- `load_skill()`：加载指定技能内容
- `get_always_skills()`：获取所有常驻技能
- `build_skills_summary()`：构建 XML 格式的技能摘要

---

### 4.2 技能文件格式

```yaml
---
name: skill-name
description: 技能描述
metadata:
  finchbot:
    emoji: 
    always: false
    requires:
      bins: [curl, jq]
      env: [API_KEY]
---
# 技能内容（Markdown）
```

---

## 5. 通道模块 (`finchbot.channels`)

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

## 6. 配置模块 (`finchbot.config`)

### 6.1 `Config`（根配置）

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

**说明**：
- 自动合并默认配置、`~/.finchbot/config.json` 和环境变量
- 环境变量优先级最高（前缀 `FINCHBOT_`）

---

### 6.3 配置结构

```
Config（根）
 language
 default_model
 agents
    defaults
 providers
    openai
    anthropic
    deepseek
    moonshot
    dashscope
    groq
    gemini
    openrouter
    custom
 tools
     web.search
     exec
     restrict_to_workspace
```

---

## 7. 国际化模块 (`finchbot.i18n`)

### 7.1 `I18nLoader`

国际化加载器。

```python
class I18nLoader:
    def __init__(self, locale: str = "en-US"): ...
    
    def get(self, key: str, default: str = "") -> str: ...
    def t(self, key: str, **kwargs) -> str: ...
```

**方法**：
- `get()`：获取翻译文本
- `t()`：获取翻译文本并替换变量

**示例**：
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
| `en-US` | 英语 |

---

## 8. 提供商模块 (`finchbot.providers`)

### 8.1 `create_chat_model`

创建聊天模型。

```python
def create_chat_model(
    provider: str,
    model: str,
    config: Config,
) -> BaseChatModel:
```

**参数**：
- `provider`：提供商名称
- `model`：模型名称
- `config`：配置对象

**返回值**：
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
| OpenRouter | （多种模型） | `OPENROUTER_API_KEY` |

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

---

## 9. MCP 模块

FinchBot 使用官方 `langchain-mcp-adapters` 库集成 MCP（Model Context Protocol）支持，支持 stdio 和 HTTP 两种传输方式。

### 9.1 概述

MCP 工具通过 `ToolFactory` 类自动加载，无需手动管理客户端连接。

```python
from finchbot.tools.factory import ToolFactory
from finchbot.config import load_config
from pathlib import Path

config = load_config()
factory = ToolFactory(config, Path("./workspace"))

# 创建所有工具（包括 MCP 工具）
all_tools = await factory.create_all_tools()
```

---

### 9.2 `ToolFactory` MCP 方法

```python
class ToolFactory:
    async def create_all_tools(self) -> list[BaseTool]:
        """创建所有工具（包括 MCP 工具）"""
        ...
    
    async def _load_mcp_tools(self) -> list[BaseTool]:
        """使用 langchain-mcp-adapters 加载 MCP 工具"""
        ...
    
    def _build_mcp_server_config(self) -> dict:
        """构建 MCP 服务器配置"""
        ...
```

**方法说明**：
- `create_all_tools()`：创建内置工具 + MCP 工具的完整列表
- `_load_mcp_tools()`：内部方法，使用 `MultiServerMCPClient` 加载 MCP 工具
- `_build_mcp_server_config()`：将 FinchBot 配置转换为 langchain-mcp-adapters 格式

---

### 9.3 MCP 配置结构

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
    """MCP 总配置"""
    servers: dict[str, MCPServerConfig] = {}
```

---

### 9.4 传输方式

#### stdio 传输

适用于本地 MCP 服务器，通过命令行启动：

```json
{
  "command": "mcp-server-filesystem",
  "args": ["/path/to/workspace"],
  "env": {}
}
```

#### HTTP 传输

适用于远程 MCP 服务器，通过 HTTP 连接：

```json
{
  "url": "https://api.example.com/mcp",
  "headers": {
    "Authorization": "Bearer your-token"
  }
}
```

---

### 9.5 使用示例

```python
import asyncio
from pathlib import Path
from finchbot.tools.factory import ToolFactory
from finchbot.config import load_config

async def main():
    config = load_config()
    factory = ToolFactory(config, Path("./workspace"))
    
    # 获取所有工具（内置 + MCP）
    tools = await factory.create_all_tools()
    
    print(f"加载了 {len(tools)} 个工具")
    
    # 清理资源
    await factory.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 9.6 配置示例

```json
{
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "mcp-filesystem",
        "args": ["/path/to/allowed/dir"],
        "env": {}
      },
      "remote-api": {
        "url": "https://api.example.com/mcp",
        "headers": {
          "Authorization": "Bearer your-token"
        }
      },
      "github": {
        "command": "mcp-github",
        "args": [],
        "env": {
          "GITHUB_TOKEN": "ghp_..."
        },
        "disabled": true
      }
    }
  }
}
```

---

### 9.7 依赖

MCP 功能需要安装 `langchain-mcp-adapters`：

```bash
pip install langchain-mcp-adapters
```

或使用 uv：

```bash
uv add langchain-mcp-adapters
```

---

## 10. 能力构建模块 (`finchbot.agent.capabilities`)

### 10.1 `CapabilitiesBuilder`

智能体能力构建器，负责构建 Agent 能力相关的系统提示词。

```python
class CapabilitiesBuilder:
    def __init__(self, config: Config, tools: Sequence[BaseTool] | None = None): ...
    
    def build_capabilities_prompt(self) -> str: ...
    def get_mcp_server_count(self) -> int: ...
    def get_mcp_tool_count(self) -> int: ...
```

**功能**：
- 构建 MCP 服务器配置信息
- 列出可用的 MCP 工具
- 提供 Channel 配置状态
- 生成扩展指南

**使用示例**：
```python
from finchbot.agent.capabilities import CapabilitiesBuilder, write_capabilities_md
from finchbot.config import load_config
from pathlib import Path

config = load_config()
builder = CapabilitiesBuilder(config, tools)

# 获取能力描述
capabilities = builder.build_capabilities_prompt()

# 写入文件
write_capabilities_md(Path("./workspace"), config, tools)
```

---

## 11. 工具生成模块 (`finchbot.tools.tools_generator`)

### 11.1 `ToolsGenerator`

工具信息自动生成器，用于生成 TOOLS.md 文件。

```python
class ToolsGenerator:
    def __init__(
        self, 
        workspace: Path | None = None,
        tools: Sequence[BaseTool] | None = None
    ): ...
    
    def generate_tools_content(self) -> str: ...
    def write_to_file(self, filename: str = "TOOLS.md") -> Path | None: ...
```

**功能**：
- 从 ToolRegistry 或外部工具列表生成工具文档
- 自动识别 MCP 工具并单独分类
- 支持按类别分组工具

**使用示例**：
```python
from finchbot.tools.tools_generator import ToolsGenerator
from pathlib import Path

generator = ToolsGenerator(workspace=Path("./workspace"), tools=tools)

# 生成内容
content = generator.generate_tools_content()

# 写入文件
generator.write_to_file("TOOLS.md")
```
