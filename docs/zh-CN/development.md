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

**生产环境**（普通用户）：

```bash
uv sync
```

**开发环境**（贡献者）：

```bash
uv sync --extra dev
```

> **说明**：
> - `uv sync` 安装生产依赖
> - `--extra dev` 额外安装开发工具：pytest、ruff、basedpyright
> - 嵌入模型（~95MB）会在首次运行时自动下载到 `.models/fastembed/`，无需手动干预。

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

## 自动化机制

FinchBot 采用**运行时懒加载 (Runtime Lazy Loading)** 策略管理大文件依赖：

1.  **安装阶段**: `uv sync` 仅安装 Python 依赖库，不下载模型。
2.  **运行阶段**: 当用户执行 `finchbot chat` 时：
    - 系统检测 `.models/fastembed` 目录。
    - 如果模型不存在，自动选择最佳镜像（国内/国外）并下载。
    - 下载完成后无缝进入应用。

这种设计避免了构建隔离带来的问题，并确保了国内用户的下载体验。
