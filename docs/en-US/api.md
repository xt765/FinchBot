# API Reference

## Core Modules

### 1. Agent (`finchbot.agent`)

FinchBot's core agent logic, built on LangGraph.

- **`create_finch_agent(model, workspace, ...)`**: Creates and configures an Agent instance.
- **`ContextBuilder`**: Dynamically builds system prompts, managing System Prompt, Memory Guide, and Skills.

### 2. Memory (`finchbot.memory`)

Layered memory system responsible for managing short-term and long-term memory.

- **`MemoryManager`**: Unified entry point for the memory system.
    - `remember(content, ...)`: Save a new memory.
    - `recall(query, ...)`: Retrieve relevant memories.
    - `forget(pattern)`: Delete or archive memories.
- **`SQLiteStore`**: Structured storage based on SQLite.
- **`VectorMemoryStore`**: Vector storage based on ChromaDB/FastEmbed.

### 3. Tools (`finchbot.tools`)

Tool ecosystem.

- **`ToolRegistry`**: Registry managing all available tools.
- **`BaseTool`**: Base class for all tools.
- **Built-in Tools**:
    - `ReadFileTool`: Read file content.
    - `WriteFileTool`: Write file content.
    - `WebSearchTool`: Web search (DuckDuckGo/Tavily).
    - `ExecTool`: Secure shell command execution.

## Helper Modules

### Configuration (`finchbot.config`)

- **`Config`**: Pydantic model defining configuration structure.
- **`load_config()`**: Load and merge configuration (File + Env).

### I18n (`finchbot.i18n`)

- **`t(key, **kwargs)`**: Get translated text.
- **`I18n`**: Internationalization loader.
