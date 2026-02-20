# API Reference

This document provides detailed API reference for FinchBot's core classes and methods.

## 1. Agent Module (`finchbot.agent`)

### 1.1 `create_finch_agent`

Creates and configures a FinchBot agent instance.

```python
def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, SqliteSaver | MemorySaver]:
```

**Parameters**:
- `model`: Base chat model instance (e.g., `ChatOpenAI`, `ChatAnthropic`)
- `workspace`: Workspace directory path (`Path` object), used for file operations, memory storage, etc.
- `tools`: Available tools sequence (optional, defaults to None). If provided, Agent will automatically bind them
- `use_persistent`: Whether to enable persistent storage (Checkpointing). Default is `True`, which saves conversation history to SQLite

**Returns**:
- `(agent, checkpointer)` tuple:
    - `agent`: Compiled LangGraph state graph, can call `.invoke()` or `.stream()`
    - `checkpointer`: Persistent storage object (`SqliteSaver` instance)

**Example**:
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

Dynamic system prompt builder.

```python
class ContextBuilder:
    def __init__(self, workspace: Path): ...
    
    def build_system_prompt(self, skill_names, use_cache=True) -> str: ...
```

**Methods**:
- `build_system_prompt()`: Generates complete system prompt string. It combines:
    - `SYSTEM.md`: Base role definition
    - `MEMORY_GUIDE.md`: Memory usage guidelines
    - `SKILL.md`: Dynamically loaded skill descriptions
    - `TOOLS.md`: Auto-generated tool documentation
    - Runtime info (OS, Time, Python Version)

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
- `category`: Category (optional, e.g., "personal", "work"). If not provided, will be auto-inferred
- `importance`: Importance score (0.0-1.0, optional). If not provided, will be auto-calculated
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
    - `KEYWORD_ONLY`: Pure keyword retrieval (1.0/0.0)
    - `SEMANTIC_ONLY`: Pure semantic retrieval (0.0/1.0)
    - `FACTUAL`: Factual query (0.8/0.2)
    - `CONCEPTUAL`: Conceptual query (0.2/0.8)
    - `COMPLEX`: Complex query (0.5/0.5)
    - `AMBIGUOUS`: Ambiguous query (0.3/0.7)
- `similarity_threshold`: Similarity threshold (default 0.5)
- `include_archived`: Whether to include archived memories (default False)

**Returns**:
- List of memory dictionaries, each containing `id`, `content`, `category`, `importance`, `similarity`, etc.

#### `forget`

Delete or archive memories.

```python
def forget(self, pattern: str) -> dict[str, Any]:
```

**Parameters**:
- `pattern`: String to match memory content (supports partial matching)

**Returns**:
- Deletion statistics dictionary containing `total_found`, `deleted`, `archived`, `pattern` fields

#### Usage Example

```python
from finchbot.memory import MemoryManager, QueryType
from pathlib import Path

# Initialize
manager = MemoryManager(Path.home() / ".finchbot" / "workspace")

# Save memory (auto-classification + importance scoring)
memory = manager.remember(
    content="User prefers dark theme, likes clean interface design",
    category="preference",  # Can be manually specified or auto-inferred
    importance=0.8
)

# Retrieve memory - semantic priority
results = manager.recall(
    query="user interface preferences",
    query_type=QueryType.CONCEPTUAL,  # Conceptual query
    top_k=5
)

# Retrieve memory - keyword priority
results = manager.recall(
    query="what is my email",
    query_type=QueryType.FACTUAL,  # Factual query
    top_k=3
)

# Delete memory
stats = manager.forget("old email")
```

---

## 3. Tools Module (`finchbot.tools`)

All tools inherit from `finchbot.tools.base.FinchTool`.

### 3.1 `FinchTool` (Base Class)

```python
class FinchTool(BaseTool):
    name: str
    description: str
    parameters: ClassVar[dict[str, Any]]
    
    def _run(self, *args, **kwargs) -> Any: ...
    async def _arun(self, *args, **kwargs) -> Any: ...
```

### 3.2 Creating Custom Tools

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
        # Implement your logic
        return f"Result: {input_text}"
```

### 3.3 Built-in Tools

| Tool Class | Tool Name (`name`) | Description | Key Parameters |
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
- `get_always_skills()`: Get all always-on skills (`always: true`)
- `build_skills_summary()`: Build XML format skill summary

---

## 5. Config Module (`finchbot.config`)

### 5.1 `Config` (Root Config)

Pydantic model defining the entire application's configuration structure.

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

Load configuration.

```python
def load_config() -> Config: ...
```

**Description**:
- Automatically merges default config, `~/.finchbot/config.json`, and environment variables
- Environment variables have highest priority (prefix `FINCHBOT_`)

---

## 6. I18n Module (`finchbot.i18n`)

### 6.1 `I18nLoader`

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

# Simple translation
text = i18n.get("cli.help")

# Translation with variables
text = i18n.t("cli.chat.session", session_id="abc123")
```
