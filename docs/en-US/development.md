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
> - The embedding model (~95MB) will be automatically downloaded to `.models/fastembed/` on first run. No manual action required.

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

## Automation Mechanism

FinchBot uses a **Runtime Lazy Loading** strategy for large file dependencies:

1.  **Installation Phase**: `uv sync` only installs Python dependencies, skipping model downloads.
2.  **Runtime Phase**: When the user executes `finchbot chat`:
    - The system checks the `.models/fastembed` directory.
    - If the model is missing, it automatically selects the best mirror (Domestic/International) and downloads it.
    - Once downloaded, it seamlessly enters the application.

This design avoids issues with build isolation and ensures a smooth download experience for users worldwide.
