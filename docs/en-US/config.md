# Configuration Guide

FinchBot supports configuration via `config.json` file and environment variables. Environment variables take precedence over the configuration file.

## 1. Configuration File (`~/.finchbot/config.json`)

The default configuration file is located in the `.finchbot` directory in the user's home directory.

```json
{
  "language": "en-US",
  "default_model": "gpt-5",
  "providers": {
    "openai": {
      "api_key": "sk-...",
      "api_base": "https://api.openai.com/v1"
    }
  }
}
```

### Configuration Items

- **`language`**: System language, supports `zh-CN` (Simplified Chinese), `en-US` (English), and `zh-HK` (Traditional Chinese). Default: `en-US`.
- **`default_model`**: Name of the default model to use. Default: `gpt-5`.
- **`agents`**: Agent behavior configuration.
    - `defaults.workspace`: Agent workspace directory. Default: `~/.finchbot/workspace`.
    - `defaults.temperature`: Model temperature (0.0-1.0). Default: `0.7`.
    - `defaults.max_tokens`: Maximum output tokens. Default: `8192`.
    - `defaults.max_tool_iterations`: Maximum tool calls per conversation. Default: `20`.
- **`providers`**: API configuration for each LLM provider.
    - `api_key`: API Key.
    - `api_base`: API Base URL (optional, for custom or proxy).
    - `models`: List of available models (optional).
    - `openai_compatible`: Whether compatible with OpenAI API format.
- **`tools`**: Tool-specific configuration.
    - `restrict_to_workspace`: Whether to restrict file operations to workspace. Default: `false`.
    - `web.search.max_results`: Maximum search results. Default: `5`.
    - `web.search.api_key`: Tavily API Key.
    - `web.search.brave_api_key`: Brave Search API Key.
    - `exec.timeout`: Shell command timeout in seconds. Default: `60`.

## 2. Environment Variables

You can configure using a `.env` file (in the project root) or system environment variables.

| Provider | API Key Variable | API Base Variable |
| --- | --- | --- |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_API_BASE` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_BASE` |
| Gemini | `GOOGLE_API_KEY` | - |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API_BASE` |
| Groq | `GROQ_API_KEY` | `GROQ_API_BASE` |
| Moonshot | `MOONSHOT_API_KEY` | `MOONSHOT_API_BASE` |
| DashScope | `DASHSCOPE_API_KEY` | `DASHSCOPE_API_BASE` |
| OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_API_BASE` |
| Tavily (Search) | `TAVILY_API_KEY` | - |
| Brave (Search) | `BRAVE_API_KEY` | - |

## 3. Logging Configuration

Logs are stored by default in the `logs/` directory of the workspace, rotated daily.

- **`--verbose` / `-v`**: Enable detailed debug logs (DEBUG level).
- **`--quiet` / `-q`**: Quiet mode, output only errors (ERROR level).
