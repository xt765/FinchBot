# 开发指南

## 环境搭建

### 1. 安装 UV

FinchBot 使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理和虚拟环境隔离。

```bash
# Windows
curl -LsSf https://astral.sh/uv/install.ps1 | powershell -c -

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆仓库

```bash
git clone https://github.com/yourusername/finchbot.git
cd finchbot
```

### 3. 安装依赖

```bash
uv sync --dev
```

## 测试

### 运行单元测试

```bash
uv run pytest
```

### 运行覆盖率测试

```bash
uv run pytest --cov=src --cov-report=html
```
查看 `htmlcov/index.html` 报告。

## 代码质量

### 格式化

```bash
uv run ruff format .
```

### 代码检查

```bash
uv run ruff check .
```

### 类型检查

```bash
uv run basedpyright
```

## 目录结构

- **`src/finchbot`**: 源码目录
    - **`agent`**: 智能体逻辑
    - **`memory`**: 记忆系统
    - **`tools`**: 工具集
    - **`i18n`**: 国际化
    - **`cli`**: 命令行界面
    - **`config`**: 配置管理
- **`tests`**: 测试目录
- **`docs`**: 文档目录
