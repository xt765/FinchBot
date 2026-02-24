# 贡献指南

感谢您对 FinchBot 的兴趣！我们欢迎各种形式的贡献，包括代码、文档、设计、测试和反馈。

## 目录

1. [快速开始](#1-快速开始)
2. [开发流程](#2-开发流程)
3. [代码风格](#3-代码风格)
4. [提交规范](#4-提交规范)
5. [文档贡献](#5-文档贡献)
6. [行为准则](#6-行为准则)

---

## 1. 快速开始

### 贡献流程

```mermaid
flowchart LR
    classDef step fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1,rx:10,ry:10;

    A["1. Fork 仓库"]:::step --> B["2. 创建分支"]:::step
    B --> C["3. 编写代码"]:::step
    C --> D["4. 提交 PR"]:::step
    D --> E["5. 代码审查"]:::step
    E --> F["6. 合并"]:::step
```

### 1.1 Fork 仓库

在 GitHub 或 Gitee 上 Fork 项目到您的账户。

### 1.2 创建分支

基于 `main` 分支创建您的功能分支：

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 1.3 开发

- 遵循代码风格指南 (Ruff)
- 添加单元测试覆盖新功能
- 确保所有测试通过
- 使用 `uv run` 执行本地测试

### 1.4 提交 Pull Request

将您的分支 Push 到 GitHub，并创建一个 Pull Request。请在 PR 描述中详细说明您的更改。

---

## 2. 开发流程

### 2.1 环境准备

```bash
# 安装开发依赖
uv sync --extra dev

# 配置 pre-commit hooks（可选）
pre-commit install
```

### 2.2 开发检查清单

```mermaid
flowchart TD
    classDef check fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef pass fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef fail fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;

    A[代码格式化<br/>ruff format]:::check --> B{通过?}
    B -->|是| C[代码检查<br/>ruff check]:::check
    B -->|否| A
    C --> D{通过?}
    D -->|是| E[类型检查<br/>basedpyright]:::check
    D -->|否| F[修复问题]:::fail
    F --> C
    E --> G{通过?}
    G -->|是| H[单元测试<br/>pytest]:::check
    G -->|否| I[修复类型]:::fail
    I --> E
    H --> J{通过?}
    J -->|是| K([可以提交]):::pass
    J -->|否| L[修复测试]:::fail
    L --> H
```

### 2.3 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_memory.py

# 运行覆盖率测试
uv run pytest --cov=src --cov-report=html
```

---

## 3. 代码风格

### 3.1 格式化工具

使用 **Ruff** 进行代码格式化和检查：

```bash
# 格式化代码
uv run ruff format .

# 检查代码
uv run ruff check .

# 自动修复
uv run ruff check --fix .
```

### 3.2 类型提示

必须使用 **Type Hints**，通过 BasedPyright 检查：

```python
# 好的示例
def remember(self, content: str, category: str | None = None) -> str:
    ...

# 不好的示例
def remember(self, content, category=None):
    ...
```

### 3.3 文档字符串

使用 **Google Style Docstrings**：

```python
def recall(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """检索相关记忆.

    Args:
        query: 查询文本.
        top_k: 返回结果数量.

    Returns:
        记忆字典列表.

    Raises:
        ValueError: 如果查询为空.
    """
    ...
```

---

## 4. 提交规范

### 4.1 Conventional Commits

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### 4.2 提交类型

| 类型 | 说明 | 示例 |
| :--- | :--- | :--- |
| `feat` | 新功能 | `feat: add memory recall tool` |
| `fix` | Bug 修复 | `fix: handle api timeout error` |
| `docs` | 文档更新 | `docs: update installation guide` |
| `style` | 代码格式 | `style: format with ruff` |
| `refactor` | 重构 | `refactor: simplify memory manager` |
| `test` | 测试 | `test: add unit tests for tools` |
| `chore` | 杂项 | `chore: update dependencies` |

### 4.3 提交示例

```bash
# 好的提交
git commit -m "feat: add web search fallback to DuckDuckGo"
git commit -m "fix: handle empty query in recall tool"
git commit -m "docs: update architecture diagram"

# 不好的提交
git commit -m "update code"
git commit -m "fix bug"
git commit -m "changes"
```

---

## 5. 文档贡献

### 5.1 文档结构

```
docs/
├── zh-CN/              # 中文文档
│   ├── architecture.md
│   ├── api.md
│   ├── config.md
│   ├── deployment.md
│   ├── development.md
│   ├── contributing.md
│   ├── guide/
│   │   ├── usage.md
│   │   └── extension.md
│   └── blog/
└── en-US/              # 英文文档
    └── ...
```

### 5.2 文档规范

1. **同步更新**: 修改代码时同步更新相关文档
2. **双语维护**: 中文和英文文档保持一致
3. **Mermaid 图表**: 使用 Mermaid 绘制架构图和流程图
4. **代码示例**: 提供可运行的代码示例

### 5.3 Mermaid 图表风格

```mermaid
flowchart TD
    classDef startEnd fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    A([开始]):::startEnd --> B[处理]:::process
    B --> C{判断}:::decision
    C -->|是| D([结束]):::startEnd
    C -->|否| B
```

---

## 6. 行为准则

- 尊重所有贡献者
- 保持专业和友好的交流
- 接受建设性批评
- 关注对社区最有利的事情

---

## 联系方式

- **Issues**: [GitHub Issues](https://github.com/xt765/finchbot/issues)
- **Pull Requests**: [GitHub PRs](https://github.com/xt765/finchbot/pulls)
- **Gitee**: [Gitee 仓库](https://gitee.com/xt765/finchbot)

感谢您的贡献！🎉
