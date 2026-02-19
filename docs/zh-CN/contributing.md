# 贡献指南

感谢您对 FinchBot 的兴趣！我们欢迎各种形式的贡献，包括代码、文档、设计、测试和反馈。

## 如何贡献

### 1. Fork 仓库

在 GitHub 上 Fork 项目到您的账户。

### 2. 创建分支

基于 `main` 分支创建您的功能分支。

```bash
git checkout -b feature/your-feature-name
```

### 3. 开发

- 遵循代码风格指南 (Ruff)。
- 添加单元测试覆盖新功能。
- 确保所有测试通过。
- 使用 `uv run` 执行本地测试。

### 4. 提交 Pull Request

将您的分支 Push 到 GitHub，并创建一个 Pull Request。请在 PR 描述中详细说明您的更改。

## 代码风格

- **格式化**: 使用 Ruff (自动格式化)。
- **类型提示**: 必须使用 Type Hints (`typing`)，通过 BasedPyright 检查。
- **文档**: 使用 Google Style Docstrings，并保持中文注释。
- **提交信息**: 遵循 Conventional Commits (如 `feat: add memory recall`, `fix: handle api timeout`)。

## 文档

- 文档位于 `docs/` 目录，分为中文 (`zh-CN`) 和英文 (`en-US`)。
- 请确保文档与代码同步更新。
