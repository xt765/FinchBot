# FinchBot (雀翎)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**FinchBot** is a lightweight, modular AI Agent framework built on LangChain and LangGraph. It is designed to provide a flexible and scalable foundation for building intelligent assistants with persistent memory, tool usage capabilities, and multi-language support.

[中文文档](../zh-CN/README.md) | [English Documentation](README.md)

## ✨ Features

- **🧠 Powerful Memory System**: Layered memory architecture based on SQLite and vector databases, supporting automatic classification, importance scoring, and forgetting mechanisms.
- **🔌 Modular Tools**: Easily extensible tool system with built-in file operations, web search, shell execution, and more.
- **🌍 Multi-language Support**: Complete i18n support with automatic system language detection and easy switching between English and Chinese interfaces.
- **🛠️ Developer Friendly**: Clear code structure, comprehensive Type Hints, and detailed documentation comments.
- **🚀 Modern Tech Stack**: Python 3.13+, LangGraph, UV, Ruff, Pydantic v2.

## 🚀 Quick Start

### Prerequisites

- Windows / Linux / macOS
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (Recommended)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/finchbot.git
    cd finchbot
    ```

2.  Create environment and install dependencies using uv:
    ```bash
    uv sync
    ```

3.  Configure environment variables:
    Copy `.env.example` to `.env` and fill in your API Key.
    ```bash
    cp .env.example .env
    ```

### Usage

Start an interactive chat session:

```bash
uv run finchbot chat
```

View help:

```bash
uv run finchbot --help
```

## 📖 Documentation

Detailed documentation is available in the `docs/` directory:

- [API Reference](api.md)
- [Configuration Guide](config.md)
- [Deployment Guide](deployment.md)
- [Development Guide](development.md)
- [Contributing Guide](contributing.md)

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](contributing.md) for more information.

## 📄 License

This project is licensed under the [MIT License](../../LICENSE).
