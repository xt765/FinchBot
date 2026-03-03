# API Reference

This document provides detailed API reference for FinchBot's core classes and methods.

## Table of Contents

1. [Agent Module](#1-agent-module-finchbotagent)
2. [Memory Module](#2-memory-module-finchbotmemory)
3. [Tools Module](#3-tools-module-finchbottools)
4. [Skill Module](#4-skill-module-finchbotagentskills)
5. [Channel Module](#5-channel-module-finchbotchannels)
6. [Config Module](#6-config-module-finchbotconfig)
7. [I18n Module](#7-i18n-module-finchboti18n)
8. [Providers Module](#8-providers-module-finchbotproviders)
9. [MCP Module](#9-mcp-module-finchbotmcp)

---

## 1. Agent Module (`finchbot.agent`)

### 1.1 `AgentFactory`

Factory class for assembling and configuring Agent instances.

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

**Parameters**:
- `session_id`: Session ID
- `workspace`: Workspace directory path
- `model`: Base chat model instance
- `config`: Configuration object

**Returns**:
- `(agent, checkpointer, tools)` tuple

---

### 1.2 `create_finch_agent`

Creates and configures a FinchBot agent instance.

```python
async def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, AsyncSqliteSaver | MemorySaver]:
```

**Parameters**:
- `model`: Base chat model instance (e.g., `ChatOpenAI`, `ChatAnthropic`)
- `workspace`: Workspace directory path (`Path` object)
- `tools`: Available tools sequence (optional, defaults to None)
- `use_persistent`: Whether to enable persistent storage (Checkpointing)

**Returns**:
- `(agent, checkpointer)` tuple:
    - `agent`: Compiled LangGraph state graph
    - `checkpointer`: Persistent storage object

**Example**:
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
        {"messages": [("user", "Hello!")]}, 
        config={"configurable": {"thread_id": "1"}}
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 1.3 `ContextBuilder`

Dynamic system prompt builder.

```python
class ContextBuilder:
    def __init__(self, workspace: Path): ...
    
    def build_system_prompt(self, skill_names, use_cache=True) -> str: ...
```

**Methods**:
- `build_system_prompt()`: Generates complete system prompt string

**Prompt Components**:
- `SYSTEM.md`: Base role definition
- `MEMORY_GUIDE.md`: Memory usage guidelines
- `SOUL.md`: Soul definition (personality)
- `AGENT_CONFIG.md`: Agent configuration
- `SKILL.md`: Dynamically loaded skill descriptions
- `TOOLS.md`: Auto-generated tool documentation
- `CAPABILITIES.md`: Auto-generated MCP and capability info
- Runtime info (OS, Time, Python Version)

---

### 1.4 `get_sqlite_checkpointer`

Gets SQLite persistence checkpoint.

```python
def get_sqlite_checkpointer(db_path: Path) -> SqliteSaver:
```

**Parameters**:
- `db_path`: SQLite database file path

**Returns**:
- `SqliteSaver` instance

---

## 2. Memory Module (`finchbot.memory`)

### 2.1 `MemoryManager`

Unified entry point for the memory system.

```python
class MemoryManager:
    def __init__(
        self, 
        workspace: Path, 
        embedding_model: str = "BAAI/bge-small-zh-v1.5"
    ): ...
```

#### `remember`

Save a new memory.

```python
def remember(
    self,
    content: str,
    category: str | None = None,
    importance: float | None = None,
    tags: list[str] | None = None,
) -> str:
```

**Parameters**:
- `content`: Memory text content
- `category`: Category (optional, e.g., "personal", "work")
- `importance`: Importance score (0.0-1.0, optional)
- `tags`: Tag list (optional)

**Returns**:
- `memory_id`: Newly created memory ID (UUID)

#### `recall`

Retrieve relevant memories.

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

**Parameters**:
- `query`: Query text (natural language)
- `top_k`: Number of results to return (default 5)
- `category`: Filter by category (optional)
- `query_type`: Query type (default `QueryType.COMPLEX`)
- `similarity_threshold`: Similarity threshold (default 0.5)
- `include_archived`: Whether to include archived memories (default False)

**QueryType Enum**:

| Type | Description | Keyword Weight | Semantic Weight |
|:---|:---|:---:|:---:|
| `KEYWORD_ONLY` | Pure keyword retrieval | 1.0 | 0.0 |
| `SEMANTIC_ONLY` | Pure semantic retrieval | 0.0 | 1.0 |
| `FACTUAL` | Factual query | 0.8 | 0.2 |
| `CONCEPTUAL` | Conceptual query | 0.2 | 0.8 |
| `COMPLEX` | Complex query | 0.5 | 0.5 |
| `AMBIGUOUS` | Ambiguous query | 0.3 | 0.7 |

**Returns**:
- List of memory dictionaries, each containing `id`, `content`, `category`, `importance`, `similarity`, etc.

#### `forget`

Delete or archive memories.

```python
def forget(self, pattern: str) -> dict[str, Any]:
```

**Parameters**:
- `pattern`: String to match memory content

**Returns**:
- Deletion statistics dictionary

#### Other Methods

```python
def get_stats(self) -> dict: ...
def search_memories(self, query: str, ...) -> list[dict]: ...
def get_recent_memories(self, days: int = 7, limit: int = 20) -> list[dict]: ...
def get_important_memories(self, min_importance: float = 0.8, limit: int = 20) -> list[dict]: ...
```

#### Usage Example

```python
from finchbot.memory import MemoryManager, QueryType
from pathlib import Path

manager = MemoryManager(Path.home() / ".finchbot" / "workspace")

memory = manager.remember(
    content="User prefers dark theme",
    category="preference",
    importance=0.8
)

results = manager.recall(
    query="user interface preferences",
    query_type=QueryType.CONCEPTUAL,
    top_k=5
)

stats = manager.forget("old email")
```

---

### 2.2 `QueryType`

Query type enumeration.

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

## 3. Tools Module (`finchbot.tools`)

### 3.1 `FinchTool` (Base Class)

Base class for all tools.

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

Tool factory class.

```python
class ToolFactory:
    @staticmethod
    def create_default_tools(
        workspace: Path,
        config: Config,
        session_metadata_store: SessionMetadataStore | None = None,
    ) -> list[BaseTool]:
```

**Parameters**:
- `workspace`: Workspace directory path
- `config`: Configuration object
- `session_metadata_store`: Session metadata store (optional)

**Returns**:
- List of tools

---

### 3.3 `ToolRegistry`

Tool registry (singleton pattern).

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

### 3.4 Creating Custom Tools

```python
from finchbot.tools.base import FinchTool
from typing import Any, ClassVar

class MyCustomTool(FinchTool):
    """Custom tool example."""
    
    name: str = "my_custom_tool"
    description: str = "My custom tool description"
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "input_text": {
                "type": "string",
                "description": "Input text"
            }
        },
        "required": ["input_text"]
    }
    
    def _run(self, input_text: str) -> str:
        return f"Result: {input_text}"
```

---

### 3.5 Built-in Tools

| Tool Class | Tool Name | Description | Key Parameters |
|:---|:---|:---|:---|
| `ReadFileTool` | `read_file` | Read file content | `file_path`: File path |
| `WriteFileTool` | `write_file` | Write file content | `file_path`: Path, `content`: Content |
| `EditFileTool` | `edit_file` | Edit file content | `file_path`: Path, `old_text`: Old text, `new_text`: New text |
| `ListDirTool` | `list_dir` | List directory contents | `dir_path`: Directory path |
| `ExecTool` | `exec` | Execute Shell command | `command`: Command string |
| `WebSearchTool` | `web_search` | Web search | `query`: Query, `max_results`: Max results |
| `WebExtractTool` | `web_extract` | Extract web content | `urls`: URL list |
| `RememberTool` | `remember` | Save memory | `content`: Content, `category`: Category |
| `RecallTool` | `recall` | Retrieve memory | `query`: Query, `query_type`: Query type |
| `ForgetTool` | `forget` | Delete memory | `pattern`: Match pattern |
| `SessionTitleTool` | `session_title` | Manage session title | `action`: get/set, `title`: Title |
| `ConfigureMCPTool` | `configure_mcp` | Dynamically configure MCP servers | `action`: add/update/remove/enable/disable/list, `server_name`, `command`, `args`, `env`, `url` |
| `RefreshCapabilitiesTool` | `refresh_capabilities` | Refresh capabilities file | None |
| `GetCapabilitiesTool` | `get_capabilities` | Get current capabilities | None |
| `GetMCPConfigPathTool` | `get_mcp_config_path` | Get MCP config file path | None |
| `StartBackgroundTaskTool` | `start_background_task` | Start background task | `task_description`: Task description, `agent_type`: Agent type |
| `CheckTaskStatusTool` | `check_task_status` | Check background task status | `job_id`: Task ID |
| `GetTaskResultTool` | `get_task_result` | Get background task result | `job_id`: Task ID |
| `CancelTaskTool` | `cancel_task` | Cancel background task | `job_id`: Task ID |
| `CreateCronTool` | `create_cron` | Create scheduled task | `name`: Name, `schedule`: Cron expression, `message`: Content |
| `ListCronsTool` | `list_crons` | List scheduled tasks | `include_disabled`: Include disabled tasks |
| `DeleteCronTool` | `delete_cron` | Delete scheduled task | `cron_id`: Task ID |
| `ToggleCronTool` | `toggle_cron` | Enable/disable scheduled task | `cron_id`: Task ID, `enabled`: Enable |

---

## 4. Skill Module (`finchbot.agent.skills`)

### 4.1 `SkillsLoader`

Skill loader.

```python
class SkillsLoader:
    def __init__(self, workspace: Path): ...
    
    def list_skills(self, use_cache: bool = True) -> list[dict]: ...
    def load_skill(self, name: str, use_cache: bool = True) -> str | None: ...
    def get_always_skills(self) -> list[str]: ...
    def build_skills_summary(self) -> str: ...
```

**Methods**:
- `list_skills()`: Scan and list all available skills
- `load_skill()`: Load specified skill content
- `get_always_skills()`: Get all always-on skills
- `build_skills_summary()`: Build XML format skill summary

---

### 4.2 Skill File Format

```yaml
---
name: skill-name
description: Skill description
metadata:
  finchbot:
    emoji: 
    always: false
    requires:
      bins: [curl, jq]
      env: [API_KEY]
---
# Skill content (Markdown)
```

---

## 5. Channel Module (`finchbot.channels`)

### 5.1 `BaseChannel`

Abstract base class for channels.

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

Async message router.

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

Channel manager.

```python
class ChannelManager:
    def __init__(self, bus: MessageBus): ...
    
    def register_channel(self, channel: BaseChannel) -> None: ...
    def unregister_channel(self, channel_id: str) -> None: ...
    async def start_all(self) -> None: ...
    async def stop_all(self) -> None: ...
```

---

### 5.4 Message Models

```python
class InboundMessage(BaseModel):
    """Inbound message"""
    channel_id: str
    user_id: str
    content: str
    session_id: str | None = None
    metadata: dict = {}

class OutboundMessage(BaseModel):
    """Outbound message"""
    channel_id: str
    user_id: str
    content: str
    session_id: str | None = None
    metadata: dict = {}
```

---

## 6. Config Module (`finchbot.config`)

### 6.1 `Config` (Root Config)

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

Load configuration.

```python
def load_config() -> Config: ...
```

**Description**:
- Automatically merges default config, `~/.finchbot/config.json`, and environment variables
- Environment variables have highest priority (prefix `FINCHBOT_`)

---

### 6.3 Configuration Structure

```
Config (Root)
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

## 7. I18n Module (`finchbot.i18n`)

### 7.1 `I18nLoader`

Internationalization loader.

```python
class I18nLoader:
    def __init__(self, locale: str = "en-US"): ...
    
    def get(self, key: str, default: str = "") -> str: ...
    def t(self, key: str, **kwargs) -> str: ...
```

**Methods**:
- `get()`: Get translated text
- `t()`: Get translated text with variable substitution

**Example**:
```python
from finchbot.i18n import I18nLoader

i18n = I18nLoader("en-US")

text = i18n.get("cli.help")
text = i18n.t("cli.chat.session", session_id="abc123")
```

---

### 7.2 Supported Languages

| Language Code | Language Name |
|:---|:---|
| `zh-CN` | Simplified Chinese |
| `zh-HK` | Traditional Chinese |
| `en-US` | English |

---

## 8. Providers Module (`finchbot.providers`)

### 8.1 `create_chat_model`

Create chat model.

```python
def create_chat_model(
    provider: str,
    model: str,
    config: Config,
) -> BaseChatModel:
```

**Parameters**:
- `provider`: Provider name
- `model`: Model name
- `config`: Configuration object

**Returns**:
- `BaseChatModel` instance

---

### 8.2 Supported Providers

| Provider | Model Examples | Environment Variable |
|:---|:---|:---|
| OpenAI | gpt-5, gpt-5.2, o3-mini | `OPENAI_API_KEY` |
| Anthropic | claude-sonnet-4.5, claude-opus-4.6 | `ANTHROPIC_API_KEY` |
| DeepSeek | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` |
| Gemini | gemini-2.5-flash | `GOOGLE_API_KEY` |
| Groq | llama-4-scout, llama-4-maverick | `GROQ_API_KEY` |
| Moonshot | kimi-k1.5, kimi-k2.5 | `MOONSHOT_API_KEY` |
| OpenRouter | (various models) | `OPENROUTER_API_KEY` |

---

### 8.3 Usage Example

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

## 9. MCP Module

FinchBot uses the official `langchain-mcp-adapters` library for MCP (Model Context Protocol) integration, supporting both stdio and HTTP transports.

### 9.1 Overview

MCP tools are automatically loaded through the `ToolFactory` class, no manual client connection management needed.

```python
from finchbot.tools.factory import ToolFactory
from finchbot.config import load_config
from pathlib import Path

config = load_config()
factory = ToolFactory(config, Path("./workspace"))

# Create all tools (including MCP tools)
all_tools = await factory.create_all_tools()
```

---

### 9.2 `ToolFactory` MCP Methods

```python
class ToolFactory:
    async def create_all_tools(self) -> list[BaseTool]:
        """Create all tools (including MCP tools)"""
        ...
    
    async def _load_mcp_tools(self) -> list[BaseTool]:
        """Load MCP tools using langchain-mcp-adapters"""
        ...
    
    def _build_mcp_server_config(self) -> dict:
        """Build MCP server configuration"""
        ...
```

**Method Descriptions**:
- `create_all_tools()`: Creates complete list of built-in + MCP tools
- `_load_mcp_tools()`: Internal method, uses `MultiServerMCPClient` to load MCP tools
- `_build_mcp_server_config()`: Converts FinchBot config to langchain-mcp-adapters format

---

### 9.3 MCP Configuration Structure

```python
class MCPServerConfig(BaseModel):
    """Single MCP server configuration
    
    Supports both stdio and HTTP transports.
    """
    command: str = ""           # Startup command for stdio transport
    args: list[str] = []        # Command arguments for stdio transport
    env: dict[str, str] | None = None  # Environment variables for stdio transport
    url: str = ""               # Server URL for HTTP transport
    headers: dict[str, str] | None = None  # Request headers for HTTP transport
    disabled: bool = False      # Whether to disable this server

class MCPConfig(BaseModel):
    """MCP total configuration"""
    servers: dict[str, MCPServerConfig] = {}
```

---

### 9.4 Transport Types

#### stdio Transport

Suitable for local MCP servers, started via command line:

```json
{
  "command": "mcp-server-filesystem",
  "args": ["/path/to/workspace"],
  "env": {}
}
```

#### HTTP Transport

Suitable for remote MCP servers, connected via HTTP:

```json
{
  "url": "https://api.example.com/mcp",
  "headers": {
    "Authorization": "Bearer your-token"
  }
}
```

---

### 9.5 Usage Example

```python
import asyncio
from pathlib import Path
from finchbot.tools.factory import ToolFactory
from finchbot.config import load_config

async def main():
    config = load_config()
    factory = ToolFactory(config, Path("./workspace"))
    
    # Get all tools (built-in + MCP)
    tools = await factory.create_all_tools()
    
    print(f"Loaded {len(tools)} tools")
    
    # Cleanup resources
    await factory.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 9.6 Configuration Example

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

### 9.7 Dependencies

MCP functionality requires installing `langchain-mcp-adapters`:

```bash
pip install langchain-mcp-adapters
```

Or using uv:

```bash
uv add langchain-mcp-adapters
```

---

## 10. Capabilities Module (`finchbot.agent.capabilities`)

### 10.1 `CapabilitiesBuilder`

Agent capabilities builder, responsible for building capability-related system prompts.

```python
class CapabilitiesBuilder:
    def __init__(self, config: Config, tools: Sequence[BaseTool] | None = None): ...
    
    def build_capabilities_prompt(self) -> str: ...
    def get_mcp_server_count(self) -> int: ...
    def get_mcp_tool_count(self) -> int: ...
```

**Features**:
- Build MCP server configuration info
- List available MCP tools
- Provide Channel configuration status
- Generate extension guides

**Usage Example**:
```python
from finchbot.agent.capabilities import CapabilitiesBuilder, write_capabilities_md
from finchbot.config import load_config
from pathlib import Path

config = load_config()
builder = CapabilitiesBuilder(config, tools)

# Get capabilities description
capabilities = builder.build_capabilities_prompt()

# Write to file
write_capabilities_md(Path("./workspace"), config, tools)
```

---

## 11. Tools Generator Module (`finchbot.tools.tools_generator`)

### 11.1 `ToolsGenerator`

Tool information auto-generator for generating TOOLS.md files.

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

**Features**:
- Generate tool documentation from ToolRegistry or external tool list
- Auto-identify MCP tools and categorize separately
- Support grouping tools by category

**Usage Example**:
```python
from finchbot.tools.tools_generator import ToolsGenerator
from pathlib import Path

generator = ToolsGenerator(workspace=Path("./workspace"), tools=tools)

# Generate content
content = generator.generate_tools_content()

# Write to file
generator.write_to_file("TOOLS.md")
```

---

## 12. Background Tasks Module (`finchbot.agent.tools.background`)

### 12.1 `JobManager`

Background task manager (singleton pattern), responsible for managing all background task execution.

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

**Method Descriptions**:
- `set_subagent_manager()`: Set subagent manager (for independent Agent loop execution)
- `start_task()`: Start a background task, returns task ID
- `check_status()`: Check task status (pending/running/completed/failed/cancelled)
- `get_result()`: Get completed task result
- `cancel_task()`: Cancel a running task
- `cancel_all_tasks()`: Cancel all running tasks

**Task Status**:

| Status | Description |
| :--- | :--- |
| `pending` | Task waiting to execute |
| `running` | Task is executing (includes iteration progress) |
| `completed` | Task completed successfully |
| `failed` | Task execution failed |
| `cancelled` | Task was cancelled |

---

### 12.2 `SubagentManager`

Subagent manager, responsible for independent Agent loop execution.

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

**Parameter Descriptions**:
- `model`: LLM model instance
- `workspace`: Workspace path
- `tools`: Available tools list
- `config`: Configuration object
- `on_notify`: Callback when task completes `(session_key, label, result) -> None`

**Method Descriptions**:
- `start_task()`: Start independent Agent loop task, max 15 iterations
- `cancel_task()`: Cancel specified task
- `cancel_all_tasks()`: Cancel all tasks
- `get_running_tasks()`: Get list of running tasks

**Iteration Limit**:
- Each Subagent task executes max 15 Agent iterations
- Prevents infinite loops, ensures task termination

---

### 12.2 Background Task Tools

#### `StartBackgroundTaskTool`

Start a background task.

```python
class StartBackgroundTaskTool(FinchTool):
    name: str = "start_background_task"
    description: str = "Start a background task..."
    
    def _run(
        self,
        task_description: str,
        agent_type: str = "default",
    ) -> str: ...
```

**Parameters**:
- `task_description`: Task description, detailed explanation of the task
- `agent_type`: Agent type (default/research/writer)

**Returns**:
- Task ID (UUID)

---

#### `CheckTaskStatusTool`

Check background task status.

```python
class CheckTaskStatusTool(FinchTool):
    name: str = "check_task_status"
    description: str = "Check the status of a background task..."
    
    def _run(self, job_id: str) -> str: ...
```

**Parameters**:
- `job_id`: Task ID

**Returns**:
- Task status info (JSON format)

---

#### `GetTaskResultTool`

Get completed task result.

```python
class GetTaskResultTool(FinchTool):
    name: str = "get_task_result"
    description: str = "Get the detailed result of a completed task..."
    
    def _run(self, job_id: str) -> str: ...
```

**Parameters**:
- `job_id`: Task ID

**Returns**:
- Task result (only available when status is completed)

---

#### `CancelTaskTool`

Cancel a running background task.

```python
class CancelTaskTool(FinchTool):
    name: str = "cancel_task"
    description: str = "Cancel a running background task..."
    
    def _run(self, job_id: str) -> str: ...
```

**Parameters**:
- `job_id`: Task ID

**Returns**:
- Cancel result (success/failure)

---

### 12.3 Usage Example

```python
from finchbot.agent.tools.background import JobManager
from finchbot.config import load_config
from pathlib import Path

async def main():
    config = load_config()
    workspace = Path.home() / ".finchbot" / "workspace"
    
    manager = JobManager.get_instance()
    
    # Start background task
    job_id = await manager.start_task(
        task_description="Analyze project code structure",
        agent_type="research",
        config=config,
        workspace=workspace,
    )
    
    # Check status
    status = await manager.check_status(job_id)
    print(f"Task status: {status['status']}")
    
    # Get result
    if status["status"] == "completed":
        result = await manager.get_result(job_id)
        print(f"Task result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 13. Scheduled Tasks Module (`finchbot.cron`)

### 13.1 Data Classes

#### `CronSchedule`

Schedule configuration, supports three scheduling modes.

```python
@dataclass
class CronSchedule:
    """Schedule configuration"""
    at: str | None = None           # One-time task: ISO format time
    every_seconds: int | None = None  # Interval task: seconds
    cron_expr: str | None = None    # Cron expression: minute hour day month weekday
```

**Three Scheduling Modes**:

| Mode | Parameter | Description | Example |
| :--- | :--- | :--- | :--- |
| **at** | `at="2025-01-15T10:30:00"` | One-time task, deleted after execution | Meeting reminder |
| **every** | `every_seconds=3600` | Interval task, runs every N seconds | Health check |
| **cron** | `cron_expr="0 9 * * *"` | Cron expression | Daily report |

---

#### `CronPayload`

Task content configuration.

```python
@dataclass
class CronPayload:
    """Task content"""
    name: str                       # Task name
    message: str                    # Task message/instruction
    tz: str = "local"               # IANA timezone (e.g. Asia/Shanghai)
    input_data: dict | None = None  # Optional input data
```

---

#### `CronJobState`

Task execution state.

```python
@dataclass
class CronJobState:
    """Execution state"""
    last_run: datetime | None = None   # Last execution time
    next_run: datetime | None = None   # Next execution time
    last_result: str | None = None     # Last execution result
    run_count: int = 0                  # Execution count
```

---

#### `CronJob`

Complete scheduled task.

```python
@dataclass
class CronJob:
    """Complete scheduled task"""
    id: str                          # Task ID (UUID)
    schedule: CronSchedule           # Schedule configuration
    payload: CronPayload             # Task content
    state: CronJobState              # Execution state
    enabled: bool = True             # Is enabled
    created_at: datetime             # Creation time
```

---

### 13.2 `CronService`

Scheduled task service, supports three scheduling modes and IANA timezone.

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

**Parameter Descriptions**:
- `workspace`: Workspace path
- `on_deliver`: Message delivery callback `(channel, target_id, message) -> None`

**Method Descriptions**:
- `start()`: Start scheduled task service (async)
- `stop()`: Stop scheduled task service (sync)
- `create_job()`: Create scheduled task (supports three modes)
- `delete_job()`: Delete scheduled task
- `toggle_job()`: Enable/disable scheduled task
- `list_jobs()`: List all scheduled tasks
- `get_job()`: Get specified task
- `get_job_state()`: Get task execution state
- `run_job_now()`: Execute scheduled task immediately

**IANA Timezone Support**:

```python
# Supported timezone examples
tz="Asia/Shanghai"      # Shanghai timezone
tz="America/New_York"   # New York timezone
tz="Europe/London"      # London timezone
tz="local"              # System local timezone (default)
```

**Cron Expression Format**: `minute hour day month weekday`

| Expression | Description |
| :--- | :--- |
| `0 9 * * *` | Daily at 9 AM |
| `0 */2 * * *` | Every 2 hours |
| `30 18 * * 1-5` | Weekdays at 6:30 PM |
| `0 0 1 * *` | First day of month at midnight |

---

### 13.3 Scheduled Task Tools

#### `CreateCronTool`

Create a scheduled task (supports three scheduling modes).

```python
class CreateCronTool(FinchTool):
    name: str = "create_cron"
    description: str = "Create a scheduled task..."
    
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

**Parameters**:
- `name`: Task name
- `message`: Task content/instruction
- `at`: One-time task time (ISO format, e.g. `2025-01-15T10:30:00`)
- `every_seconds`: Interval seconds (e.g. `3600` for hourly)
- `cron_expr`: Cron expression (5 fields: minute hour day month weekday)
- `tz`: IANA timezone (e.g. `Asia/Shanghai`, default `local`)
- `input_data`: Optional input data (JSON format)

**Note**: Only one of the three scheduling modes needs to be specified (`at`, `every_seconds`, or `cron_expr`).

---

#### `RunCronNowTool`

Execute a scheduled task immediately.

```python
class RunCronNowTool(FinchTool):
    name: str = "run_cron_now"
    description: str = "Execute a scheduled task immediately..."
    
    def _run(self, cron_id: str) -> str: ...
```

**Parameters**:
- `cron_id`: Task ID

---

#### `GetCronStatusTool`

Get scheduled task execution state.

```python
class GetCronStatusTool(FinchTool):
    name: str = "get_cron_status"
    description: str = "Get the execution state of a scheduled task..."
    
    def _run(self, cron_id: str) -> str: ...
```

**Parameters**:
- `cron_id`: Task ID

**Returns**:
- Task state info (includes last run time, next run time, execution count, etc.)

---

#### `ListCronsTool`

List all scheduled tasks.

```python
class ListCronsTool(FinchTool):
    name: str = "list_crons"
    description: str = "List all scheduled tasks..."
    
    def _run(self, include_disabled: bool = False) -> str: ...
```

**Parameters**:
- `include_disabled`: Whether to include disabled tasks

---

#### `DeleteCronTool`

Delete a scheduled task.

```python
class DeleteCronTool(FinchTool):
    name: str = "delete_cron"
    description: str = "Delete a scheduled task..."
    
    def _run(self, cron_id: str) -> str: ...
```

**Parameters**:
- `cron_id`: Task ID

---

#### `ToggleCronTool`

Enable or disable a scheduled task.

```python
class ToggleCronTool(FinchTool):
    name: str = "toggle_cron"
    description: str = "Enable or disable a scheduled task..."
    
    def _run(self, cron_id: str, enabled: bool) -> str: ...
```

**Parameters**:
- `cron_id`: Task ID
- `enabled`: Whether to enable (true/false)

---

### 13.4 Usage Example

```python
from finchbot.cron.service import CronService
from pathlib import Path

async def main():
    workspace = Path.home() / ".finchbot" / "workspace"
    
    # Create service (with message delivery callback)
    async def on_deliver(channel: str, target_id: str, message: str):
        print(f"[{channel}] {target_id}: {message}")
    
    service = CronService(workspace, on_deliver=on_deliver)
    
    # Mode 1: One-time task (at)
    job_id_1 = service.create_job(
        name="Meeting Reminder",
        message="Remind me to attend the meeting",
        at="2025-01-15T10:30:00",
        tz="America/New_York"
    )
    
    # Mode 2: Interval task (every)
    job_id_2 = service.create_job(
        name="Health Check",
        message="Check system status",
        every_seconds=3600  # Every hour
    )
    
    # Mode 3: Cron expression (cron)
    job_id_3 = service.create_job(
        name="Daily Report",
        message="Send daily report",
        cron_expr="0 9 * * *",  # Daily at 9:00
        tz="America/New_York"
    )
    
    # List all tasks
    jobs = service.list_jobs()
    for job in jobs:
        print(f"{job.payload.name}: {job.schedule}")
    
    # Get task state
    state = service.get_job_state(job_id_1)
    print(f"Next run: {state.next_run}")
    
    # Execute immediately
    result = await service.run_job_now(job_id_3)
    
    # Start service
    await service.start()
    
    # Stop service
    service.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 14. Heartbeat Service Module (`finchbot.heartbeat`)

### 14.1 `HeartbeatService`

Heartbeat service that periodically checks the HEARTBEAT.md file for pending tasks.

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

**Parameters**:
- `workspace`: Workspace path
- `interval`: Check interval (seconds, default 300)
- `config`: Configuration object

**How It Works**:
1. Periodically reads the `HEARTBEAT.md` file in the workspace root
2. Uses LLM to analyze file content and determine if there are pending tasks
3. If there are pending tasks, triggers the corresponding processing flow

**HEARTBEAT.md Example**:

```markdown
# Heartbeat Tasks

Add tasks that need periodic checking to this file.

Examples:
- [ ] Check email
- [ ] Review schedule
- [ ] Review goals
```

---

### 14.2 Usage Example

```python
from finchbot.heartbeat.service import HeartbeatService
from finchbot.config import load_config
from pathlib import Path

async def main():
    config = load_config()
    workspace = Path.home() / ".finchbot" / "workspace"
    
    service = HeartbeatService(
        workspace=workspace,
        interval=300,  # 5 minutes
        config=config,
    )
    
    # Start service
    await service.start()
    
    # Check status
    print(f"Service running: {service.is_running()}")
    
    # Stop service
    await service.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 15. Progress Streaming Module (`finchbot.agent.streaming`)

### 15.1 Progress Output Functions

Utility functions for real-time progress feedback.

#### `emit_progress`

Send a progress update message.

```python
def emit_progress(message: str) -> None:
    """Send a progress update message.
    
    Args:
        message: Progress message content.
    """
```

**Usage Example**:
```python
from finchbot.agent.streaming import emit_progress

emit_progress("Analyzing files...")
emit_progress("Processing 50% complete")
```

---

#### `emit_tool_call`

Send a tool call notification.

```python
def emit_tool_call(tool_name: str, args: dict | None = None) -> None:
    """Send a tool call notification.
    
    Args:
        tool_name: Tool name.
        args: Tool arguments (optional).
    """
```

**Usage Example**:
```python
from finchbot.agent.streaming import emit_tool_call

emit_tool_call("read_file", {"file_path": "/path/to/file"})
emit_tool_call("web_search", {"query": "Python async"})
```

---

### 15.2 `ProgressReporter`

Progress reporter class with richer progress reporting functionality.

```python
class ProgressReporter:
    def __init__(self, writer: StreamWriter | None = None): ...
    
    def report(self, message: str, progress_type: str = "status") -> None: ...
    
    def report_thinking(self, message: str = "Thinking...") -> None: ...
    
    def report_tool_call(self, tool_name: str, args: dict | None = None) -> None: ...
    
    def report_result(self, result: str) -> None: ...
    
    def report_error(self, error: str) -> None: ...
```

**Method Descriptions**:
- `report()`: Send a general progress report
- `report_thinking()`: Send thinking status
- `report_tool_call()`: Send tool call notification
- `report_result()`: Send result
- `report_error()`: Send error information

---

### 15.3 Usage Example

```python
from finchbot.agent.streaming import ProgressReporter

# Create progress reporter
reporter = ProgressReporter()

# Report progress
reporter.report_thinking("Analyzing problem...")
reporter.report_tool_call("read_file", {"file_path": "data.json"})
reporter.report_result("File read successfully")
reporter.report_error("File not found")
```

---

### 15.4 Progress Types

| Type | Description |
|:---|:---|
| `thinking` | Thinking status |
| `tool_call` | Tool call |
| `result` | Execution result |
| `error` | Error information |
| `status` | General status |

---

## 16. Webhook Server Module (`finchbot.channels.webhook_server`)

### 16.1 `WebhookServer`

FastAPI Webhook server for receiving LangBot messages and returning AI responses.

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

**Parameters**:
- `config`: Configuration object
- `workspace`: Workspace path
- `host`: Listen address (default `0.0.0.0`)
- `port`: Listen port (default 8000)

---

### 16.2 Webhook Request Models

#### `WebhookRequest`

```python
class WebhookRequest(BaseModel):
    """Webhook request model"""
    event: str                    # Event type
    user_id: str                  # User ID
    session_id: str | None = None # Session ID
    message: str                  # Message content
    platform: str = "unknown"     # Platform identifier
    metadata: dict = {}           # Additional metadata
```

#### `WebhookResponse`

```python
class WebhookResponse(BaseModel):
    """Webhook response model"""
    success: bool                 # Success status
    response: str | None = None   # AI response content
    error: str | None = None      # Error message
    session_id: str | None = None # Session ID
```

---

### 16.3 Usage Example

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
    
    # Start server
    await server.start()
    
    # Server running...
    # Visit http://localhost:8000/docs for API documentation
    
    # Stop server
    await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 16.4 CLI Startup

```bash
# Use default port 8000
uv run finchbot webhook

# Specify port
uv run finchbot webhook --port 9000

# Specify host and port
uv run finchbot webhook --host 127.0.0.1 --port 8000
```

---

### 16.5 API Endpoints

| Endpoint | Method | Description |
|:---|:---:|:---|
| `/webhook` | POST | Receive LangBot messages |
| `/health` | GET | Health check |
| `/docs` | GET | API documentation (Swagger UI) |

---

### 16.6 Integration with LangBot

1. Start FinchBot Webhook server:
   ```bash
   uv run finchbot webhook --port 8000
   ```

2. Start LangBot:
   ```bash
   uvx langbot
   ```

3. Configure Webhook URL in LangBot WebUI:
   ```
   http://localhost:8000/webhook
   ```

4. Configure platforms (QQ, WeChat, Feishu, etc.), messages will be forwarded to FinchBot via Webhook.
