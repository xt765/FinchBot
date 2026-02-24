# Configuration Guide

FinchBot uses a flexible hierarchical configuration system that supports **configuration files** and **environment variables**.

Priority: **Environment Variables** > **User Config File** (`~/.finchbot/config.json`) > **Default Values**

## Table of Contents

1. [Configuration File Structure](#1-configuration-file-structure)
2. [Environment Variables](#2-environment-variables)
3. [Quick Setup](#3-quick-setup)
4. [Example Configurations](#4-example-configurations)

---

## 1. Configuration File Structure

The user configuration file is located at `~/.finchbot/config.json` by default.

### Root Object

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `language` | string | `"en-US"` | Interface and prompt language. Supports `zh-CN`, `zh-HK`, `en-US`. |
| `language_set_by_user` | boolean | `false` | Whether language was manually set by user (for auto-detection). |
| `default_model` | string | `"gpt-5"` | Default LLM model name to use. |
| `default_model_set_by_user` | boolean | `false` | Whether default model was manually set by user. |
| `agents` | object | - | Agent behavior configuration. |
| `providers` | object | - | LLM provider configuration. |
| `tools` | object | - | Tool-specific configuration. |

### `agents` Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `defaults.workspace` | string | `~/.finchbot/workspace` | Agent workspace directory. All file operations will be restricted to this directory. |
| `defaults.model` | string | `"gpt-5"` | Default model to use. |
| `defaults.temperature` | float | `0.7` | Model temperature (0.0-1.0). 0.0 is most deterministic, 1.0 is most creative. |
| `defaults.max_tokens` | int | `8192` | Maximum output tokens. |
| `defaults.max_tool_iterations` | int | `20` | Maximum tool calls per conversation (prevents infinite loops). |

### `providers` Configuration

Supported providers: `openai`, `anthropic`, `gemini`, `deepseek`, `moonshot`, `dashscope`, `groq`, `openrouter`, `custom`.

Each provider contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `api_key` | string | API Key. Recommended to configure via environment variables. |
| `api_base` | string | API Base URL. For proxies or self-hosted models. |
| `extra_headers` | dict | Additional request headers (optional). |
| `models` | list[str] | List of supported models for this provider (optional). |
| `openai_compatible` | bool | Whether compatible with OpenAI API format (default: true). |

**Built-in Provider List**:

| Provider | Description | Env Var Prefix |
|----------|-------------|-----------------|
| `openai` | OpenAI Official | `OPENAI_*` |
| `anthropic` | Anthropic Claude | `ANTHROPIC_*` |
| `gemini` | Google Gemini | `GOOGLE_*` |
| `deepseek` | DeepSeek | `DEEPSEEK_*` |
| `moonshot` | Moonshot (Kimi) | `MOONSHOT_*` |
| `dashscope` | Alibaba Cloud Tongyi | `DASHSCOPE_*` |
| `groq` | Groq | `GROQ_*` |
| `openrouter` | OpenRouter | `OPENROUTER_*` |
| `custom` | Custom Providers | None |

### `tools` Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `restrict_to_workspace` | bool | `false` | Whether to restrict file operations to workspace. Recommended to keep enabled for security. |
| `web.search.max_results` | int | `5` | Maximum number of search results per query. |
| `web.search.api_key` | string | - | Tavily Search API Key. |
| `web.search.brave_api_key` | string | - | Brave Search API Key. |
| `exec.timeout` | int | `60` | Shell command execution timeout in seconds. |

---

## 2. Environment Variables

All configuration items can be overridden via environment variables. Environment variable prefixes are typically `FINCHBOT_` or provider-specific prefixes.

Nested configuration uses double underscores `__` for separation (Pydantic Settings format).

### LLM Providers

| Provider | API Key Variable | API Base Variable |
|----------|------------------|-------------------|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_API_BASE` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_BASE` |
| Gemini | `GOOGLE_API_KEY` | - |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API_BASE` |
| Groq | `GROQ_API_KEY` | `GROQ_API_BASE` |
| Moonshot | `MOONSHOT_API_KEY` | `MOONSHOT_API_BASE` |
| DashScope | `DASHSCOPE_API_KEY` | `DASHSCOPE_API_BASE` |
| OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_API_BASE` |

### Search Tools

| Tool | API Key Variable | Note |
|------|------------------|------|
| Tavily | `TAVILY_API_KEY` | Best quality, requires API Key |
| Brave | `BRAVE_API_KEY` | Free tier, requires API Key |
| DuckDuckGo | - | No API Key required (Fallback) |

### General Configuration

| Variable Name | Corresponding Config Item | Example |
|---------------|--------------------------|---------|
| `FINCHBOT_LANGUAGE` | `language` | `zh-CN` |
| `FINCHBOT_DEFAULT_MODEL` | `default_model` | `gpt-4o` |
| `FINCHBOT_AGENTS__DEFAULTS__WORKSPACE` | `agents.defaults.workspace` | `/path/to/workspace` |
| `FINCHBOT_TOOLS__RESTRICT_TO_WORKSPACE` | `tools.restrict_to_workspace` | `true` |

---

## 3. Quick Setup

### Method 1: Interactive Configuration (Recommended)

Run the configuration wizard:

```bash
uv run finchbot config
```

This command launches an interactive interface that guides you through:
- Language selection
- Default model setup
- Provider API Key configuration
- Workspace settings

### Method 2: Manual Configuration File

1.  If no config file exists, the system will automatically create default config
2.  Edit `~/.finchbot/config.json`

### Method 3: Environment Variables

Set in `.env` file (project root):

```bash
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
FINCHBOT_LANGUAGE=en-US
FINCHBOT_DEFAULT_MODEL=gpt-4o
```

---

## 4. Example Configurations

### Minimal Configuration

```json
{
  "language": "en-US",
  "default_model": "gpt-4o",
  "providers": {
    "openai": {
      "api_key": "sk-proj-..."
    }
  }
}
```

### Full Configuration Example

```json
{
  "language": "en-US",
  "language_set_by_user": true,
  "default_model": "gpt-5",
  "default_model_set_by_user": true,
  "agents": {
    "defaults": {
      "workspace": "~/.finchbot/workspace",
      "model": "gpt-5",
      "temperature": 0.7,
      "max_tokens": 8192,
      "max_tool_iterations": 20
    }
  },
  "providers": {
    "openai": {
      "api_key": "sk-proj-...",
      "api_base": "https://api.openai.com/v1"
    },
    "anthropic": {
      "api_key": "sk-ant-..."
    },
    "deepseek": {
      "api_key": "sk-...",
      "api_base": "https://api.deepseek.com"
    },
    "moonshot": {
      "api_key": "sk-...",
      "api_base": "https://api.moonshot.cn/v1"
    },
    "custom": {
      "my-provider": {
        "api_key": "sk-...",
        "api_base": "https://my-provider.com/v1",
        "openai_compatible": true
      }
    }
  },
  "tools": {
    "restrict_to_workspace": false,
    "web": {
      "search": {
        "api_key": "tvly-...",
        "brave_api_key": "...",
        "max_results": 5
      }
    },
    "exec": {
      "timeout": 60
    }
  }
}
```

### Using DeepSeek Configuration

```json
{
  "language": "en-US",
  "default_model": "deepseek-chat",
  "providers": {
    "deepseek": {
      "api_key": "sk-...",
      "api_base": "https://api.deepseek.com"
    }
  }
}
```

### Using Local Ollama Configuration

```json
{
  "language": "en-US",
  "default_model": "llama3",
  "providers": {
    "custom": {
      "ollama": {
        "api_base": "http://localhost:11434/v1",
        "api_key": "dummy-key",
        "openai_compatible": true
      }
    }
  }
}
```

---

## Verifying Configuration

View currently configured providers:

```bash
uv run finchbot config
```

Or directly run a chat test:

```bash
uv run finchbot chat
```

---

## Configuration File Locations

- User config: `~/.finchbot/config.json`
- Environment variables: `.env` in project root (optional)
- Workspace: `~/.finchbot/workspace/` (default)
