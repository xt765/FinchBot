# Development Guide

## Environment Setup

### 1. Install UV

FinchBot uses [uv](https://github.com/astral-sh/uv) for dependency management and virtual environment isolation.

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone Repository

```bash
# Gitee (recommended for users in China)
git clone https://gitee.com/xt765/finchbot.git

# or GitHub
git clone https://github.com/xt765/finchbot.git

cd finchbot
```

### 3. Install Dependencies

```bash
# Install all dependencies (including dev dependencies and embedding model)
uv sync --all-extras
```

> **Note**:
> - `--all-extras` installs development dependencies (ruff, basedpyright, pytest, etc.)
> - The embedding model (~95MB) is automatically downloaded during build to `.models/fastembed/`
> - If model download fails, run `uv run finchbot models download` manually

## Testing

### Run Unit Tests

```bash
uv run pytest
```

### Run Coverage Tests

```bash
uv run pytest --cov=src --cov-report=html
```

View `htmlcov/index.html` for the report.

## Code Quality

### Formatting

```bash
uv run ruff format .
```

### Linting

```bash
uv run ruff check .
```

### Type Checking

```bash
uv run basedpyright src
```

## Directory Structure

- **`src/finchbot`**: Source code
    - **`agent`**: Agent logic
    - **`memory`**: Memory system
    - **`tools`**: Tools
    - **`i18n`**: Internationalization
    - **`cli`**: Command Line Interface
    - **`config`**: Configuration
    - **`utils`**: Utility functions (including model downloader)
- **`tests`**: Tests
- **`docs`**: Documentation
- **`.models`**: Local model cache (auto-generated)

## Build Mechanism

FinchBot uses [hatchling](https://hatch.pypa.io/) as the build backend, with a build hook to automatically download the embedding model during installation:

```
uv sync
    ↓
Create build isolation environment
    ↓
Install build dependencies (hatchling + fastembed)
    ↓
Execute hatch_build.py build hook
    ↓
Detect and download embedding model (if not exists)
    ↓
Generate wheel and install
```

Related configuration files:
- `pyproject.toml` - Build configuration
- `uv.toml` - UV-specific configuration (build dependencies)
- `hatch_build.py` - Build hook implementation
