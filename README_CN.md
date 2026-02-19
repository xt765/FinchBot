# FinchBot (雀翎)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**FinchBot (雀翎)** 是一个轻量级、模块化的 AI Agent 框架，基于 LangChain 和 LangGraph 构建。它旨在提供一个灵活、可扩展的基础，用于构建具有持久记忆、工具使用能力和多语言支持的智能助手。

[中文文档](docs/zh-CN/README.md) | [English Documentation](docs/en-US/README.md)

## ✨ 特性

- **🧠 强大的记忆系统**: 基于 SQLite 和向量数据库的分层记忆架构，支持自动分类、重要性评分和遗忘机制。
- **🔌 模块化工具**: 易于扩展的工具系统，内置文件操作、Web 搜索、Shell 执行等常用工具。
- **🌍 多语言支持**: 完整的 i18n 支持，自动检测系统语言，轻松切换中英文界面。
- **🛠️ 开发者友好**: 清晰的代码结构，完善的类型提示 (Type Hints)，详细的文档注释。
- **🚀 现代技术栈**: Python 3.13+, LangGraph, UV, Ruff, Pydantic v2.

## 🚀 快速开始

### 前置要求

- Windows / Linux / macOS
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (推荐)

### 安装

1.  克隆仓库：
    ```bash
    git clone https://github.com/yourusername/finchbot.git
    cd finchbot
    ```

2.  使用 uv 创建环境并安装依赖：
    ```bash
    uv sync
    ```

3.  配置环境变量：
    复制 `.env.example` 为 `.env` 并填入 API Key。
    ```bash
    cp .env.example .env
    ```

### 使用

启动交互式对话：

```bash
uv run finchbot chat
```

查看帮助：

```bash
uv run finchbot --help
```

## 📖 文档

详细文档请参考 `docs/` 目录：

- [API 接口文档](docs/zh-CN/api.md)
- [配置说明](docs/zh-CN/config.md)
- [部署指南](docs/zh-CN/deployment.md)
- [开发环境搭建](docs/zh-CN/development.md)
- [贡献指南](docs/zh-CN/contributing.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！请阅读 [贡献指南](docs/zh-CN/contributing.md) 了解更多信息。

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。
