# 配置指南

FinchBot 支持通过 `config.json` 文件和环境变量进行配置。环境变量的优先级高于配置文件。

## 1. 配置文件 (`~/.finchbot/config.json`)

默认配置文件位于用户主目录下的 `.finchbot` 目录中。

```json
{
  "language": "zh-CN",
  "default_model": "gpt-5",
  "providers": {
    "openai": {
      "api_key": "sk-...",
      "api_base": "https://api.openai.com/v1"
    }
  }
}
```

### 配置项说明

- **`language`**: 系统语言，支持 `zh-CN` (简体中文) 和 `en-US` (English)。
- **`default_model`**: 默认使用的模型名称。
- **`providers`**: 各个 LLM 提供商的 API 配置。
    - `api_key`: API 密钥。
    - `api_base`: API 基础地址（可选，用于自定义或代理）。

## 2. 环境变量

可以使用 `.env` 文件（位于项目根目录）或系统环境变量来配置。

| 提供商 | API Key 变量名 | API Base 变量名 |
| --- | --- | --- |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_API_BASE` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_BASE` |
| Gemini | `GOOGLE_API_KEY` | `GOOGLE_API_BASE` |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API_BASE` |
| Moonshot | `MOONSHOT_API_KEY` | `MOONSHOT_API_BASE` |
| DashScope | `DASHSCOPE_API_KEY` | `DASHSCOPE_API_BASE` |
| Tavily (搜索) | `TAVILY_API_KEY` | - |

## 3. 日志配置

日志默认存储在工作区 `logs/` 目录下，按日期分割。

- **`--verbose` / `-v`**: 启用详细调试日志 (DEBUG 级别)。
- **`--quiet` / `-q`**: 静默模式，只输出错误信息 (ERROR 级别)。
