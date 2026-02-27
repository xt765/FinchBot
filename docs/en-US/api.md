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
| `ConfigureMCPTool` | `configure_mcp` | Dynamically configure MCP servers | `action`, `server_name`, `command`, `args`, `env`, `url` |
| `RefreshCapabilitiesTool` | `refresh_capabilities` | Refresh capabilities file | None |
| `GetCapabilitiesTool` | `get_capabilities` | Get current capabilities | None |
| `GetMCPConfigPathTool` | `get_mcp_config_path` | Get MCP config file path | None |

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
