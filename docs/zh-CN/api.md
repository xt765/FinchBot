# API 

 FinchBot  API 

## 

1. [Agent ](#1-agent--finchbotagent)
2. [Memory ](#2-memory--finchbotmemory)
3. [Tools ](#3-tools--finchbottools)
4. [Skill ](#4-skill--finchbotagentskills)
5. [Channel ](#5-channel--finchbotchannels)
6. [Config ](#6-config--finchbotconfig)
7. [I18n ](#7-i18n--finchboti18n)
8. [Providers ](#8-providers--finchbotproviders)

---

## 1. Agent  (`finchbot.agent`)

### 1.1 `AgentFactory`

Agent  Agent 

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

****:
- `model`: 
- `workspace`: 
- `session_id`:  ID
- `config`: 
- `session_metadata_store`: 

****:
- `(agent, checkpointer, tools)` 

---

### 1.2 `create_finch_agent`

 FinchBot 

```python
async def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, AsyncSqliteSaver | MemorySaver]:
```

****:
- `model`:  ( `ChatOpenAI`, `ChatAnthropic`)
- `workspace`:  (`Path` )
- `tools`:  ( None)
- `use_persistent`:  (Checkpointing)

****:
- `(agent, checkpointer)` :
    - `agent`:  LangGraph 
    - `checkpointer`: 

****:
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



```python
class ContextBuilder:
    def __init__(self, workspace: Path): ...
    
    def build_system_prompt(self, skill_names, use_cache=True) -> str: ...
```

****:
- `build_system_prompt()`: 

****:
- `SYSTEM.md`: 
- `MEMORY_GUIDE.md`: 
- `SOUL.md`: 
- `AGENT_CONFIG.md`: Agent 
- `SKILL.md`: 
- `TOOLS.md`: 
-  (OS, Time, Python Version)

---

### 1.4 `get_sqlite_checkpointer`

 SQLite 

```python
def get_sqlite_checkpointer(db_path: Path) -> SqliteSaver:
```

****:
- `db_path`: SQLite 

****:
- `SqliteSaver` 

---

## 2. Memory  (`finchbot.memory`)

### 2.1 `MemoryManager`



```python
class MemoryManager:
    def __init__(
        self, 
        workspace: Path, 
        embedding_model: str = "BAAI/bge-small-zh-v1.5"
    ): ...
```

#### `remember`



```python
def remember(
    self,
    content: str,
    category: str | None = None,
    importance: float | None = None,
    tags: list[str] | None = None,
) -> str:
```

****:
- `content`: 
- `category`:  ( "personal", "work")
- `importance`:  (0.0-1.0)
- `tags`:  ()

****:
- `memory_id`:  ID (UUID)

#### `recall`



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

****:
- `query`:  ()
- `top_k`:  ( 5)
- `category`:  ()
- `query_type`:  ( `QueryType.COMPLEX`)
- `similarity_threshold`:  ( 0.5)
- `include_archived`:  ( False)

**QueryType **:

|  |  |  |  |
|:---|:---|:---:|:---:|
| `KEYWORD_ONLY` |  | 1.0 | 0.0 |
| `SEMANTIC_ONLY` |  | 0.0 | 1.0 |
| `FACTUAL` |  | 0.8 | 0.2 |
| `CONCEPTUAL` |  | 0.2 | 0.8 |
| `COMPLEX` |  | 0.5 | 0.5 |
| `AMBIGUOUS` |  | 0.3 | 0.7 |

****:
-  `id`, `content`, `category`, `importance`, `similarity` 

#### `forget`



```python
def forget(self, pattern: str) -> dict[str, Any]:
```

****:
- `pattern`: 

****:
- 

#### 

```python
def get_stats(self) -> dict: ...
def search_memories(self, query: str, ...) -> list[dict]: ...
def get_recent_memories(self, days: int = 7, limit: int = 20) -> list[dict]: ...
def get_important_memories(self, min_importance: float = 0.8, limit: int = 20) -> list[dict]: ...
```

#### 

```python
from finchbot.memory import MemoryManager, QueryType
from pathlib import Path

manager = MemoryManager(Path.home() / ".finchbot" / "workspace")

memory = manager.remember(
    content="",
    category="preference",
    importance=0.8
)

results = manager.recall(
    query="",
    query_type=QueryType.CONCEPTUAL,
    top_k=5
)

stats = manager.forget("")
```

---

### 2.2 `QueryType`



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

## 3. Tools  (`finchbot.tools`)

### 3.1 `FinchTool` ()



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



```python
class ToolFactory:
    @staticmethod
    def create_default_tools(
        workspace: Path,
        config: Config,
        session_metadata_store: SessionMetadataStore | None = None,
    ) -> list[BaseTool]:
```

****:
- `workspace`: 
- `config`: 
- `session_metadata_store`: 

****:
- 

---

### 3.3 `ToolRegistry`



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

### 3.4 

```python
from finchbot.tools.base import FinchTool
from typing import Any, ClassVar

class MyCustomTool(FinchTool):
    """"""
    
    name: str = "my_custom_tool"
    description: str = ""
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "input_text": {
                "type": "string",
                "description": ""
            }
        },
        "required": ["input_text"]
    }
    
    def _run(self, input_text: str) -> str:
        return f": {input_text}"
```

---

### 3.5 

|  |  |  |  |
|:---|:---|:---|:---|
| `ReadFileTool` | `read_file` |  | `file_path`:  |
| `WriteFileTool` | `write_file` |  | `file_path`: , `content`:  |
| `EditFileTool` | `edit_file` |  | `file_path`: , `old_text`: , `new_text`:  |
| `ListDirTool` | `list_dir` |  | `dir_path`:  |
| `ExecTool` | `exec` |  Shell  | `command`:  |
| `WebSearchTool` | `web_search` |  | `query`: , `max_results`:  |
| `WebExtractTool` | `web_extract` |  | `urls`: URL  |
| `RememberTool` | `remember` |  | `content`: , `category`:  |
| `RecallTool` | `recall` |  | `query`: , `query_type`:  |
| `ForgetTool` | `forget` |  | `pattern`:  |
| `SessionTitleTool` | `session_title` |  | `action`: get/set, `title`:  |

---

## 4. Skill  (`finchbot.agent.skills`)

### 4.1 `SkillsLoader`



```python
class SkillsLoader:
    def __init__(self, workspace: Path): ...
    
    def list_skills(self, use_cache: bool = True) -> list[dict]: ...
    def load_skill(self, name: str, use_cache: bool = True) -> str | None: ...
    def get_always_skills(self) -> list[str]: ...
    def build_skills_summary(self) -> str: ...
```

****:
- `list_skills()`: 
- `load_skill()`: 
- `get_always_skills()`: 
- `build_skills_summary()`:  XML 

---

### 4.2 

```yaml
---
name: skill-name
description: 
metadata:
  finchbot:
    emoji: 
    always: false
    requires:
      bins: [curl, jq]
      env: [API_KEY]
---
#  (Markdown)
```

---

## 5. Channel  (`finchbot.channels`)

### 5.1 `BaseChannel`



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



```python
class ChannelManager:
    def __init__(self, bus: MessageBus): ...
    
    def register_channel(self, channel: BaseChannel) -> None: ...
    def unregister_channel(self, channel_id: str) -> None: ...
    async def start_all(self) -> None: ...
    async def stop_all(self) -> None: ...
```

---

### 5.4 

```python
class InboundMessage(BaseModel):
    """"""
    channel_id: str
    user_id: str
    content: str
    session_id: str | None = None
    metadata: dict = {}

class OutboundMessage(BaseModel):
    """"""
    channel_id: str
    user_id: str
    content: str
    session_id: str | None = None
    metadata: dict = {}
```

---

## 6. Config  (`finchbot.config`)

### 6.1 `Config` ()

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



```python
def load_config() -> Config: ...
```

****:
- `~/.finchbot/config.json` 
-  ( `FINCHBOT_`)

---

### 6.3 

```
Config ()
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

## 7. I18n  (`finchbot.i18n`)

### 7.1 `I18nLoader`



```python
class I18nLoader:
    def __init__(self, locale: str = "en-US"): ...
    
    def get(self, key: str, default: str = "") -> str: ...
    def t(self, key: str, **kwargs) -> str: ...
```

****:
- `get()`: 
- `t()`: 

****:
```python
from finchbot.i18n import I18nLoader

i18n = I18nLoader("zh-CN")

text = i18n.get("cli.help")
text = i18n.t("cli.chat.session", session_id="abc123")
```

---

### 7.2 

|  |  |
|:---|:---|
| `zh-CN` |  |
| `zh-HK` |  |
| `en-US` |  |

---

## 8. Providers  (`finchbot.providers`)

### 8.1 `create_chat_model`



```python
def create_chat_model(
    provider: str,
    model: str,
    config: Config,
) -> BaseChatModel:
```

****:
- `provider`: 
- `model`: 
- `config`: 

****:
- `BaseChatModel` 

---

### 8.2 

|  |  |  |
|:---|:---|:---|
| OpenAI | gpt-5, gpt-5.2, o3-mini | `OPENAI_API_KEY` |
| Anthropic | claude-sonnet-4.5, claude-opus-4.6 | `ANTHROPIC_API_KEY` |
| DeepSeek | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` |
| Gemini | gemini-2.5-flash | `GOOGLE_API_KEY` |
| Groq | llama-4-scout, llama-4-maverick | `GROQ_API_KEY` |
| Moonshot | kimi-k1.5, kimi-k2.5 | `MOONSHOT_API_KEY` |
| OpenRouter | () | `OPENROUTER_API_KEY` |

---

### 8.3 

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
