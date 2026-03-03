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
    ) -> tuple[CompiledStateGraph, Any, list[Any], SubagentManager | None]:
```

**参数**：
- `session_id`：会话 ID
- `workspace`：工作区目录路径
- `model`：基础聊天模型实例
- `config`：配置对象

**返回值**：
- `(agent, checkpointer, tools, subagent_manager)` 元组
    - `agent`：编译后的 LangGraph 状态图
    - `checkpointer`：持久化存储对象
    - `tools`：工具列表
    - `subagent_manager`：子代理管理器（用于后台任务）

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
| `ConfigureMCPTool` | `configure_mcp` | 动态配置 MCP 服务器 | `action`: add/update/remove/enable/disable/list, `server_name`, `command`, `args`, `env`, `url` |
| `RefreshCapabilitiesTool` | `refresh_capabilities` | 刷新能力描述文件 | 无 |
| `GetCapabilitiesTool` | `get_capabilities` | 获取当前能力描述 | 无 |
| `GetMCPConfigPathTool` | `get_mcp_config_path` | 获取 MCP 配置文件路径 | 无 |
| `StartBackgroundTaskTool` | `start_background_task` | 启动后台任务 | `task_description`：任务描述，`agent_type`：代理类型 |
| `CheckTaskStatusTool` | `check_task_status` | 检查后台任务状态 | `job_id`：任务 ID |
| `GetTaskResultTool` | `get_task_result` | 获取后台任务结果 | `job_id`：任务 ID |
| `CancelTaskTool` | `cancel_task` | 取消后台任务 | `job_id`：任务 ID |
| `CreateCronTool` | `create_cron` | 创建定时任务 | `name`：名称，`schedule`：cron 表达式，`message`：内容 |
| `ListCronsTool` | `list_crons` | 列出定时任务 | `include_disabled`：是否包含禁用的任务 |
| `DeleteCronTool` | `delete_cron` | 删除定时任务 | `cron_id`：任务 ID |
| `ToggleCronTool` | `toggle_cron` | 启用/禁用定时任务 | `cron_id`：任务 ID，`enabled`：是否启用 |

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

---

## 12. 后台任务模块 (`finchbot.agent.tools.background`)

### 12.1 `JobManager`

后台任务管理器（单例模式），负责管理所有后台任务的执行。

```python
class JobManager:
    _instance: ClassVar[JobManager | None] = None
    
    @classmethod
    def get_instance(cls) -> JobManager: ...
    
    def set_subagent_manager(self, manager: SubagentManager) -> None: ...
    
    async def start_task(
        self,
        task_description: str,
        agent_type: str = "default",
        config: Config | None = None,
        workspace: Path | None = None,
    ) -> str: ...
    
    async def check_status(self, job_id: str) -> dict[str, Any]: ...
    
    async def get_result(self, job_id: str) -> dict[str, Any]: ...
    
    async def cancel_task(self, job_id: str) -> bool: ...
    
    async def cancel_all_tasks(self) -> int: ...
```

**方法说明**：
- `set_subagent_manager()`: 设置子代理管理器（用于独立 Agent 循环执行）
- `start_task()`: 启动后台任务，返回任务 ID
- `check_status()`: 检查任务状态（pending/running/completed/failed/cancelled）
- `get_result()`: 获取已完成任务的结果
- `cancel_task()`: 取消正在运行的任务
- `cancel_all_tasks()`: 取消所有正在运行的任务

**任务状态**：

| 状态 | 说明 |
| :--- | :--- |
| `pending` | 任务等待执行 |
| `running` | 任务正在执行（包含迭代进度） |
| `completed` | 任务执行完成 |
| `failed` | 任务执行失败 |
| `cancelled` | 任务已取消 |

---

### 12.2 `SubagentManager`

子代理管理器，负责独立 Agent 循环执行。

```python
class SubagentManager:
    def __init__(
        self,
        model: BaseChatModel,
        workspace: Path,
        tools: list[BaseTool],
        config: Config,
        on_notify: Callable[[str, str, str], Awaitable[None]] | None = None,
    ): ...
    
    async def start_task(
        self,
        task_description: str,
        session_key: str,
        label: str,
    ) -> str: ...
    
    async def cancel_task(self, task_id: str) -> bool: ...
    
    async def cancel_all_tasks(self) -> int: ...
    
    def get_running_tasks(self) -> dict[str, asyncio.Task]: ...
```

**参数说明**：
- `model`: LLM 模型实例
- `workspace`: 工作区路径
- `tools`: 可用工具列表
- `config`: 配置对象
- `on_notify`: 任务完成时的回调函数 `(session_key, label, result) -> None`

**方法说明**：
- `start_task()`: 启动独立 Agent 循环任务，最多 15 次迭代
- `cancel_task()`: 取消指定任务
- `cancel_all_tasks()`: 取消所有任务
- `get_running_tasks()`: 获取正在运行的任务列表

**迭代限制**：
- 每个 Subagent 任务最多执行 15 次 Agent 迭代
- 防止无限循环，确保任务终止

---

### 12.2 后台任务工具

#### `StartBackgroundTaskTool`

启动后台任务。

```python
class StartBackgroundTaskTool(FinchTool):
    name: str = "start_background_task"
    description: str = "启动一个后台任务..."
    
    def _run(
        self,
        task_description: str,
        agent_type: str = "default",
    ) -> str: ...
```

**参数**：
- `task_description`: 任务描述，详细说明要执行的任务
- `agent_type`: 代理类型（default/research/writer）

**返回值**：
- 任务 ID（UUID）

---

#### `CheckTaskStatusTool`

检查后台任务状态。

```python
class CheckTaskStatusTool(FinchTool):
    name: str = "check_task_status"
    description: str = "检查后台任务的状态..."
    
    def _run(self, job_id: str) -> str: ...
```

**参数**：
- `job_id`: 任务 ID

**返回值**：
- 任务状态信息（JSON 格式）

---

#### `GetTaskResultTool`

获取已完成任务的结果。

```python
class GetTaskResultTool(FinchTool):
    name: str = "get_task_result"
    description: str = "获取已完成任务的详细结果..."
    
    def _run(self, job_id: str) -> str: ...
```

**参数**：
- `job_id`: 任务 ID

**返回值**：
- 任务结果（仅在状态为 completed 时可用）

---

#### `CancelTaskTool`

取消正在运行的后台任务。

```python
class CancelTaskTool(FinchTool):
    name: str = "cancel_task"
    description: str = "取消正在运行的后台任务..."
    
    def _run(self, job_id: str) -> str: ...
```

**参数**：
- `job_id`: 任务 ID

**返回值**：
- 取消结果（成功/失败）

---

### 12.3 使用示例

```python
from finchbot.agent.tools.background import JobManager
from finchbot.config import load_config
from pathlib import Path

async def main():
    config = load_config()
    workspace = Path.home() / ".finchbot" / "workspace"
    
    manager = JobManager.get_instance()
    
    # 启动后台任务
    job_id = await manager.start_task(
        task_description="分析项目代码结构",
        agent_type="research",
        config=config,
        workspace=workspace,
    )
    
    # 检查状态
    status = await manager.check_status(job_id)
    print(f"任务状态: {status['status']}")
    
    # 获取结果
    if status["status"] == "completed":
        result = await manager.get_result(job_id)
        print(f"任务结果: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 13. 定时任务模块 (`finchbot.cron`)

### 13.1 数据类

#### `CronSchedule`

调度配置，支持三种调度模式。

```python
@dataclass
class CronSchedule:
    """调度配置"""
    at: str | None = None           # 一次性任务：ISO 格式时间
    every_seconds: int | None = None  # 间隔任务：秒数
    cron_expr: str | None = None    # Cron 表达式：分 时 日 月 周
```

**三种调度模式**：

| 模式 | 参数 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| **at** | `at="2025-01-15T10:30:00"` | 一次性任务，执行后删除 | 会议提醒 |
| **every** | `every_seconds=3600` | 间隔任务，每 N 秒执行 | 健康检查 |
| **cron** | `cron_expr="0 9 * * *"` | Cron 表达式 | 每日早报 |

---

#### `CronPayload`

任务内容配置。

```python
@dataclass
class CronPayload:
    """任务内容"""
    name: str                       # 任务名称
    message: str                    # 任务消息/指令
    tz: str = "local"               # IANA 时区（如 Asia/Shanghai）
    input_data: dict | None = None  # 可选输入数据
```

---

#### `CronJobState`

任务执行状态。

```python
@dataclass
class CronJobState:
    """执行状态"""
    last_run: datetime | None = None   # 上次执行时间
    next_run: datetime | None = None   # 下次执行时间
    last_result: str | None = None     # 上次执行结果
    run_count: int = 0                  # 执行次数
```

---

#### `CronJob`

完整定时任务。

```python
@dataclass
class CronJob:
    """完整定时任务"""
    id: str                          # 任务 ID（UUID）
    schedule: CronSchedule           # 调度配置
    payload: CronPayload             # 任务内容
    state: CronJobState              # 执行状态
    enabled: bool = True             # 是否启用
    created_at: datetime             # 创建时间
```

---

### 13.2 `CronService`

定时任务服务，支持三种调度模式和 IANA 时区。

```python
class CronService:
    def __init__(
        self,
        workspace: Path,
        on_deliver: Callable[[str, str, str], Awaitable[None]] | None = None,
    ): ...
    
    async def start(self) -> None: ...
    
    def stop(self) -> None: ...
    
    def create_job(
        self,
        name: str,
        message: str,
        at: str | None = None,
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        tz: str = "local",
        input_data: dict | None = None,
    ) -> str: ...
    
    def delete_job(self, job_id: str) -> bool: ...
    
    def toggle_job(self, job_id: str, enabled: bool) -> bool: ...
    
    def list_jobs(self, include_disabled: bool = False) -> list[CronJob]: ...
    
    def get_job(self, job_id: str) -> CronJob | None: ...
    
    def get_job_state(self, job_id: str) -> CronJobState | None: ...
    
    async def run_job_now(self, job_id: str) -> dict: ...
```

**参数说明**：
- `workspace`: 工作区路径
- `on_deliver`: 消息传递回调 `(channel, target_id, message) -> None`

**方法说明**：
- `start()`: 启动定时任务服务（异步）
- `stop()`: 停止定时任务服务（同步）
- `create_job()`: 创建定时任务（支持三种模式）
- `delete_job()`: 删除定时任务
- `toggle_job()`: 启用/禁用定时任务
- `list_jobs()`: 列出所有定时任务
- `get_job()`: 获取指定任务
- `get_job_state()`: 获取任务执行状态
- `run_job_now()`: 立即执行定时任务

**IANA 时区支持**：

```python
# 支持的时区示例
tz="Asia/Shanghai"      # 上海时区
tz="America/New_York"   # 纽约时区
tz="Europe/London"      # 伦敦时区
tz="local"              # 系统本地时区（默认）
```

**Cron 表达式格式**：`分 时 日 月 周`

| 表达式 | 说明 |
| :--- | :--- |
| `0 9 * * *` | 每天上午 9 点 |
| `0 */2 * * *` | 每 2 小时 |
| `30 18 * * 1-5` | 工作日下午 6:30 |
| `0 0 1 * *` | 每月 1 日零点 |

---

### 13.3 定时任务工具

#### `CreateCronTool`

创建定时任务（支持三种调度模式）。

```python
class CreateCronTool(FinchTool):
    name: str = "create_cron"
    description: str = "创建一个定时任务..."
    
    def _run(
        self,
        name: str,
        message: str,
        at: str | None = None,
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        tz: str = "local",
        input_data: str | None = None,
    ) -> str: ...
```

**参数**：
- `name`: 任务名称
- `message`: 任务内容/指令
- `at`: 一次性任务时间（ISO 格式，如 `2025-01-15T10:30:00`）
- `every_seconds`: 间隔秒数（如 `3600` 表示每小时）
- `cron_expr`: Cron 表达式（5 位：分 时 日 月 周）
- `tz`: IANA 时区（如 `Asia/Shanghai`，默认 `local`）
- `input_data`: 可选的输入数据（JSON 格式）

**注意**：三种调度模式只需指定其中一种（`at`、`every_seconds` 或 `cron_expr`）。

---

#### `RunCronNowTool`

立即执行定时任务。

```python
class RunCronNowTool(FinchTool):
    name: str = "run_cron_now"
    description: str = "立即执行一次定时任务..."
    
    def _run(self, cron_id: str) -> str: ...
```

**参数**：
- `cron_id`: 任务 ID

---

#### `GetCronStatusTool`

获取定时任务执行状态。

```python
class GetCronStatusTool(FinchTool):
    name: str = "get_cron_status"
    description: str = "获取定时任务的执行状态..."
    
    def _run(self, cron_id: str) -> str: ...
```

**参数**：
- `cron_id`: 任务 ID

**返回值**：
- 任务状态信息（包含上次执行时间、下次执行时间、执行次数等）

---

#### `ListCronsTool`

列出所有定时任务。

```python
class ListCronsTool(FinchTool):
    name: str = "list_crons"
    description: str = "列出所有定时任务..."
    
    def _run(self, include_disabled: bool = False) -> str: ...
```

**参数**：
- `include_disabled`: 是否包含已禁用的任务

---

#### `DeleteCronTool`

删除定时任务。

```python
class DeleteCronTool(FinchTool):
    name: str = "delete_cron"
    description: str = "删除指定的定时任务..."
    
    def _run(self, cron_id: str) -> str: ...
```

**参数**：
- `cron_id`: 任务 ID

---

#### `ToggleCronTool`

启用或禁用定时任务。

```python
class ToggleCronTool(FinchTool):
    name: str = "toggle_cron"
    description: str = "启用或禁用定时任务..."
    
    def _run(self, cron_id: str, enabled: bool) -> str: ...
```

**参数**：
- `cron_id`: 任务 ID
- `enabled`: 是否启用（true/false）

---

### 13.4 使用示例

```python
from finchbot.cron.service import CronService
from pathlib import Path

async def main():
    workspace = Path.home() / ".finchbot" / "workspace"
    
    # 创建服务（带消息传递回调）
    async def on_deliver(channel: str, target_id: str, message: str):
        print(f"[{channel}] {target_id}: {message}")
    
    service = CronService(workspace, on_deliver=on_deliver)
    
    # 模式 1: 一次性任务 (at)
    job_id_1 = service.create_job(
        name="会议提醒",
        message="提醒我参加会议",
        at="2025-01-15T10:30:00",
        tz="Asia/Shanghai"
    )
    
    # 模式 2: 间隔任务 (every)
    job_id_2 = service.create_job(
        name="健康检查",
        message="检查系统状态",
        every_seconds=3600  # 每小时
    )
    
    # 模式 3: Cron 表达式 (cron)
    job_id_3 = service.create_job(
        name="早报",
        message="发送每日早报",
        cron_expr="0 9 * * *",  # 每天 9:00
        tz="Asia/Shanghai"
    )
    
    # 列出所有任务
    jobs = service.list_jobs()
    for job in jobs:
        print(f"{job.payload.name}: {job.schedule}")
    
    # 获取任务状态
    state = service.get_job_state(job_id_1)
    print(f"下次执行: {state.next_run}")
    
    # 立即执行一次
    result = await service.run_job_now(job_id_3)
    
    # 启动服务
    await service.start()
    
    # 停止服务
    service.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 14. 心跳服务模块 (`finchbot.heartbeat`)

### 14.1 `HeartbeatService`

心跳服务，定期检查 HEARTBEAT.md 文件中的待办事项。

```python
class HeartbeatService:
    def __init__(
        self,
        workspace: Path,
        interval: int = 300,
        config: Config | None = None,
    ): ...
    
    async def start(self) -> None: ...
    
    async def stop(self) -> None: ...
    
    def is_running(self) -> bool: ...
```

**参数**：
- `workspace`: 工作区路径
- `interval`: 检查间隔（秒，默认 300）
- `config`: 配置对象

**工作原理**：
1. 定期读取工作区根目录的 `HEARTBEAT.md` 文件
2. 使用 LLM 分析文件内容，判断是否有待处理任务
3. 如果有待处理任务，触发相应的处理流程

**HEARTBEAT.md 示例**：

```markdown
# 心跳任务

在此文件中添加需要定期检查的任务。

例如:
- [ ] 检查邮件
- [ ] 查看日程
- [ ] 回顾目标
```

---

### 14.2 使用示例

```python
from finchbot.heartbeat.service import HeartbeatService
from finchbot.config import load_config
from pathlib import Path

async def main():
    config = load_config()
    workspace = Path.home() / ".finchbot" / "workspace"
    
    service = HeartbeatService(
        workspace=workspace,
        interval=300,  # 5 分钟
        config=config,
    )
    
    # 启动服务
    await service.start()
    
    # 检查状态
    print(f"服务运行中: {service.is_running()}")
    
    # 停止服务
    await service.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 15. 进度流模块 (`finchbot.agent.streaming`)

### 15.1 进度输出函数

提供实时进度反馈的工具函数。

#### `emit_progress`

发送进度更新消息。

```python
def emit_progress(message: str) -> None:
    """发送进度更新消息。
    
    Args:
        message: 进度消息内容。
    """
```

**使用示例**：
```python
from finchbot.agent.streaming import emit_progress

emit_progress("正在分析文件...")
emit_progress("处理完成 50%")
```

---

#### `emit_tool_call`

发送工具调用通知。

```python
def emit_tool_call(tool_name: str, args: dict | None = None) -> None:
    """发送工具调用通知。
    
    Args:
        tool_name: 工具名称。
        args: 工具参数（可选）。
    """
```

**使用示例**：
```python
from finchbot.agent.streaming import emit_tool_call

emit_tool_call("read_file", {"file_path": "/path/to/file"})
emit_tool_call("web_search", {"query": "Python async"})
```

---

### 15.2 `ProgressReporter`

进度报告器类，提供更丰富的进度报告功能。

```python
class ProgressReporter:
    def __init__(self, writer: StreamWriter | None = None): ...
    
    def report(self, message: str, progress_type: str = "status") -> None: ...
    
    def report_thinking(self, message: str = "思考中...") -> None: ...
    
    def report_tool_call(self, tool_name: str, args: dict | None = None) -> None: ...
    
    def report_result(self, result: str) -> None: ...
    
    def report_error(self, error: str) -> None: ...
```

**方法说明**：
- `report()`: 发送通用进度报告
- `report_thinking()`: 发送思考状态
- `report_tool_call()`: 发送工具调用通知
- `report_result()`: 发送结果
- `report_error()`: 发送错误信息

---

### 15.3 使用示例

```python
from finchbot.agent.streaming import ProgressReporter

# 创建进度报告器
reporter = ProgressReporter()

# 报告进度
reporter.report_thinking("正在分析问题...")
reporter.report_tool_call("read_file", {"file_path": "data.json"})
reporter.report_result("文件读取成功")
reporter.report_error("文件不存在")
```

---

### 15.4 进度类型

| 类型 | 说明 |
|:---|:---|
| `thinking` | 思考状态 |
| `tool_call` | 工具调用 |
| `result` | 执行结果 |
| `error` | 错误信息 |
| `status` | 通用状态 |

---

## 16. Webhook 服务器模块 (`finchbot.channels.webhook_server`)

### 16.1 `WebhookServer`

FastAPI Webhook 服务器，用于接收 LangBot 的消息并返回 AI 响应。

```python
class WebhookServer:
    def __init__(
        self,
        config: Config,
        workspace: Path,
        host: str = "0.0.0.0",
        port: int = 8000,
    ): ...
    
    async def start(self) -> None: ...
    
    async def stop(self) -> None: ...
```

**参数**：
- `config`: 配置对象
- `workspace`: 工作区路径
- `host`: 监听地址（默认 `0.0.0.0`）
- `port`: 监听端口（默认 8000）

---

### 16.2 Webhook 请求模型

#### `WebhookRequest`

```python
class WebhookRequest(BaseModel):
    """Webhook 请求模型"""
    event: str                    # 事件类型
    user_id: str                  # 用户 ID
    session_id: str | None = None # 会话 ID
    message: str                  # 消息内容
    platform: str = "unknown"     # 平台标识
    metadata: dict = {}           # 附加元数据
```

#### `WebhookResponse`

```python
class WebhookResponse(BaseModel):
    """Webhook 响应模型"""
    success: bool                 # 是否成功
    response: str | None = None   # AI 响应内容
    error: str | None = None      # 错误信息
    session_id: str | None = None # 会话 ID
```

---

### 16.3 使用示例

```python
import asyncio
from pathlib import Path
from finchbot.channels.webhook_server import WebhookServer
from finchbot.config import load_config

async def main():
    config = load_config()
    workspace = Path.home() / ".finchbot" / "workspace"
    
    server = WebhookServer(
        config=config,
        workspace=workspace,
        host="0.0.0.0",
        port=8000,
    )
    
    # 启动服务器
    await server.start()
    
    # 服务器运行中...
    # 访问 http://localhost:8000/docs 查看 API 文档
    
    # 停止服务器
    await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 16.4 CLI 启动

```bash
# 使用默认端口 8000
uv run finchbot webhook

# 指定端口
uv run finchbot webhook --port 9000

# 指定主机和端口
uv run finchbot webhook --host 127.0.0.1 --port 8000
```

---

### 16.5 API 端点

| 端点 | 方法 | 说明 |
|:---|:---:|:---|
| `/webhook` | POST | 接收 LangBot 消息 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | API 文档（Swagger UI） |

---

### 16.6 与 LangBot 集成

1. 启动 FinchBot Webhook 服务器：
   ```bash
   uv run finchbot webhook --port 8000
   ```

2. 启动 LangBot：
   ```bash
   uvx langbot
   ```

3. 在 LangBot WebUI 中配置 Webhook URL：
   ```
   http://localhost:8000/webhook
   ```

4. 配置平台（QQ、微信、飞书等），消息将通过 Webhook 转发到 FinchBot。
