# 

 FinchBot 

## 

1. [](#1-)
2. [](#2-)
3. [](#3-)
4. [](#4-)
5. [](#5-)

---

## 1. 

### 1.1  UV

FinchBot  [uv](https://github.com/astral-sh/uv) 

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 1.2 

```bash
# Gitee
git clone https://gitee.com/xt765/finchbot.git

#  GitHub
git clone https://github.com/xt765/finchbot.git

cd finchbot
```

### 1.3 

****

```bash
uv sync
```

****

```bash
uv sync --extra dev
```

> ****
> - `uv sync` 
> - `--extra dev` pytestruffbasedpyright
> - ~95MB `.models/fastembed/`

### 1.4 

```mermaid
flowchart LR
    classDef step fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1,rx:10,ry:10;

    A["1.  uv"]:::step --> B["2. "]:::step
    B --> C["3. uv sync --extra dev"]:::step
    C --> D["4. finchbot config"]:::step
    D --> E["5. "]:::step
```

---

## 2. 

### 2.1 

```bash
uv run pytest
```

### 2.2 

```bash
uv run pytest --cov=src --cov-report=html
```

 `htmlcov/index.html` 

### 2.3 

```bash
# 
uv run pytest tests/test_memory.py

# 
uv run pytest tests/test_memory.py::test_remember

# 
uv run pytest -v tests/
```

### 2.4 

```
tests/
 test_agent.py        # Agent 
 test_memory.py       # 
 test_tools.py        # 
 test_config.py       # 
 conftest.py          #  fixtures
```

---

## 3. 

### 3.1 

```bash
uv run ruff format .
```

### 3.2 

```bash
uv run ruff check .
```

### 3.3 

```bash
uv run basedpyright src
```

### 3.4 

```mermaid
flowchart TD
    classDef startEnd fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef check fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    A([]):::startEnd --> B[ruff format]:::process
    B --> C{?}:::check
    C -->|| B
    C -->|| D[ruff check]:::process
    D --> E{Lint ?}:::check
    E -->|| F[]:::process
    F --> D
    E -->|| G[basedpyright]:::process
    G --> H{?}:::check
    H -->|| I[]:::process
    I --> G
    H -->|| J[pytest]:::process
    J --> K{?}:::check
    K -->|| L[]:::process
    L --> J
    K -->|| M([]):::startEnd
```

### 3.5 Pre-commit Hooks ()

 `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

## 4. 

```
finchbot/
 src/finchbot/          # 
    agent/             # 
       core.py       # Agent 
       factory.py    # AgentFactory
       context.py    # ContextBuilder
       skills.py     # SkillsLoader
    memory/            # 
       manager.py    # MemoryManager
       types.py      # 
       services/     # 
       storage/      # 
    tools/             # 
       base.py       # FinchTool 
       factory.py    # ToolFactory
       registry.py   # ToolRegistry
       *.py          # 
    channels/          # 
       base.py       # BaseChannel
       bus.py        # MessageBus
       manager.py    # ChannelManager
    cli/               # 
       chat_session.py
       config_manager.py
       ui.py
    config/            # 
       loader.py
       schema.py
    i18n/              # 
       loader.py
       locales/
    providers/         # LLM 
       factory.py
    server/            # Web 
       main.py       # FastAPI
       loop.py       # AgentLoop
    sessions/          # 
    utils/             # 
        logger.py
        model_downloader.py
 tests/                 # 
 docs/                  # 
    zh-CN/            # 
    en-US/            # 
 web/                   # Web 
    src/
    package.json
 .models/               # 
 pyproject.toml         # 
 uv.lock               # 
```

---

## 5. 

### 5.1 

FinchBot ** (Runtime Lazy Loading)** 

```mermaid
flowchart TD
    classDef startEnd fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    A([uv sync]):::startEnd --> B[ Python ]:::process
    B --> C([finchbot chat]):::startEnd
    C --> D{?}:::decision
    D -->|| E([]):::startEnd
    D -->|| F[]:::process
    F --> G{?}:::decision
    G -->|| H[ hf-mirror.com]:::process
    G -->|| I[ Hugging Face]:::process
    H --> J[]:::process
    I --> J
    J --> E
```

1. ****: `uv sync`  Python 
2. ****:  `finchbot chat` 
    -  `.models/fastembed` 
    - /
    - 



### 5.2 

** (Double-checked locking)** 

```python
def _register_default_tools() -> None:
    global _default_tools_registered

    if _default_tools_registered:
        return

    with _tools_registration_lock:
        if _default_tools_registered:
            return
        # ...
        _default_tools_registered = True
```

### 5.3 

FinchBot  `asyncio` + `ThreadPoolExecutor` 

|  |  |  |
| :--- | :--- | :---: |
| LLM  | ~2-5s |  |
| SQLite  | ~0.1s |  |
|  | ~0.1s |  |
|  | ~0.5s |  |

---

## 

### Q:  Agent 

```bash
#  DEBUG 
finchbot -vv chat
```

### Q: 

```python
# tests/test_tools.py
from finchbot.tools.filesystem import ReadFileTool

def test_read_file():
    tool = ReadFileTool()
    result = tool._run(file_path="test.txt")
    assert result is not None
```

### Q: 

1.  `tests/`  `test_*.py` 
2.  `pytest` 
3.  `uv run pytest` 
