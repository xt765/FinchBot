# Contributing Guide

Thank you for your interest in FinchBot! We welcome contributions of all forms, including code, documentation, design, testing, and feedback.

## How to Contribute

### 1. Fork Repository

Fork the project to your account on GitHub.

### 2. Create Branch

Create your feature branch based on the `main` branch.

```bash
git checkout -b feature/your-feature-name
```

### 3. Develop

- Follow the code style guide (Ruff).
- Add unit tests to cover new features.
- Ensure all tests pass.
- Use `uv run` to execute local tests.

### 4. Submit Pull Request

Push your branch to GitHub and create a Pull Request. Please describe your changes in detail in the PR description.

## Code Style

- **Formatting**: Use Ruff (auto-formatting).
- **Type Hints**: Must use Type Hints (`typing`), checked by BasedPyright.
- **Documentation**: Use Google Style Docstrings, and maintain Chinese comments (as per project rules, though bilingual is appreciated).
- **Commit Messages**: Follow Conventional Commits (e.g., `feat: add memory recall`, `fix: handle api timeout`).
