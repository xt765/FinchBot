# Development Guide

## Environment Setup

### 1. Install UV

FinchBot uses [uv](https://github.com/astral-sh/uv) for dependency management and virtual environment isolation.

```bash
# Windows
curl -LsSf https://astral.sh/uv/install.ps1 | powershell -c -

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone Repository

```bash
git clone https://github.com/yourusername/finchbot.git
cd finchbot
```

### 3. Install Dependencies

```bash
uv sync --dev
```

## Testing

### Run Unit Tests

```bash
uv run pytest
```

### Run Coverage Tests

```bash
uv run pytest --cov=src --cov-report=html
```
View `htmlcov/index.html` report.

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
uv run basedpyright
```

## Directory Structure

- **`src/finchbot`**: Source code
    - **`agent`**: Agent logic
    - **`memory`**: Memory system
    - **`tools`**: Tools
    - **`i18n`**: Internationalization
    - **`cli`**: Command Line Interface
    - **`config`**: Configuration
- **`tests`**: Tests
- **`docs`**: Documentation
