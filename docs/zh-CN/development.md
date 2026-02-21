# 开发指南

## 环境搭建

### 1. 安装 UV

FinchBot 使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理和虚拟环境隔离。

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆仓库

```bash
# Gitee（国内推荐）
git clone https://gitee.com/xt765/finchbot.git

# 或 GitHub
git clone https://github.com/xt765/finchbot.git

cd finchbot
```

### 3. 安装依赖

```bash
# 安装所有依赖（包括开发依赖和嵌入模型）
uv sync --all-extras
```

> **说明**：
> - `--all-extras` 会安装开发依赖（ruff、basedpyright、pytest 等）
> - 嵌入模型（约 95MB）会在构建时自动下载到 `.models/fastembed/`
> - 如果模型下载失败，可手动运行 `uv run finchbot models download`

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
uv run basedpyright src
```

## 目录结构

- **`src/finchbot`**: 源码目录
    - **`agent`**: 智能体逻辑
    - **`memory`**: 记忆系统
    - **`tools`**: 工具集
    - **`i18n`**: 国际化
    - **`cli`**: 命令行界面
    - **`config`**: 配置管理
    - **`utils`**: 工具函数（含模型下载）
- **`tests`**: 测试目录
- **`docs`**: 文档目录
- **`.models`**: 本地模型缓存（自动生成）

## 构建机制

FinchBot 使用 [hatchling](https://hatch.pypa.io/) 作为构建后端，并通过构建钩子在安装时自动下载嵌入模型：

```
uv sync
    ↓
创建构建隔离环境
    ↓
安装构建依赖（hatchling + fastembed）
    ↓
执行 hatch_build.py 构建钩子
    ↓
检测并下载嵌入模型（如不存在）
    ↓
生成 wheel 并安装
```

相关配置文件：
- `pyproject.toml` - 构建配置
- `uv.toml` - uv 特定配置（构建依赖）
- `hatch_build.py` - 构建钩子实现
