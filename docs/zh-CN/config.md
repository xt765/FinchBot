# 配置指南

FinchBot 采用灵活的层级配置系统，支持通过 **配置文件** 和 **环境变量** 进行配置。

优先级：**环境变量** > **用户配置文件** (`~/.finchbot/config.json`) > **默认配置**

## 1. 配置文件结构

用户配置文件默认位于 `~/.finchbot/config.json`。

### 根对象

| 字段 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `language` | string | `"zh-CN"` | 界面和提示词语言。支持 `zh-CN`, `en-US`。 |
| `default_model` | string | `"gpt-4o"` | 默认使用的 LLM 模型名称。 |
| `agents` | object | - | Agent 行为配置。 |
| `providers` | object | - | LLM 提供商配置。 |
| `tools` | object | - | 工具特定配置。 |

### `agents` 配置

| 字段 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `defaults.workspace` | string | `~/.finchbot/workspace` | Agent 的工作目录。所有文件操作将限制在此目录下。 |
| `defaults.temperature` | float | `0.0` | 模型的温度系数 (0.0-1.0)。0.0 最精确，1.0 最具创造性。 |
| `defaults.max_tokens` | int | `4096` | 最大输出 Token 数。 |
| `defaults.max_tool_iterations` | int | `15` | 单次对话中允许的最大工具调用次数（防止死循环）。 |

### `providers` 配置

支持以下提供商：`openai`, `anthropic`, `google` (Gemini), `deepseek`, `moonshot`, `dashscope`, `azure`, `ollama`。

每个提供商包含以下字段：

| 字段 | 类型 | 描述 |
| :--- | :--- | :--- |
| `api_key` | string | API 密钥。建议通过环境变量配置。 |
| `api_base` | string | API 基础 URL。用于代理或自托管模型。 |
| `models` | list[str] | 该提供商支持的模型列表（可选）。 |

**示例**:
```json
"providers": {
  "openai": {
    "api_key": "sk-...",
    "api_base": "https://api.openai.com/v1"
  },
  "ollama": {
    "api_base": "http://localhost:11434"
  }
}
```

### `tools` 配置

| 字段 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `restrict_to_workspace` | bool | `true` | 是否强制限制文件操作在工作区内。建议保持开启以确保安全。 |
| `web.search.max_results` | int | `5` | 每次搜索返回的最大结果数。 |
| `web.search.tavily_api_key` | string | - | Tavily 搜索 API Key。 |
| `web.search.brave_api_key` | string | - | Brave 搜索 API Key。 |
| `exec.timeout` | int | `60` | Shell 命令执行的超时时间（秒）。 |

---

## 2. 环境变量配置

所有配置项均可通过环境变量覆盖。环境变量前缀通常为 `FINCHBOT_` 或特定的提供商前缀。

### LLM 提供商

| 提供商 | API Key 变量 | API Base 变量 |
| :--- | :--- | :--- |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_API_BASE` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_BASE` |
| Google | `GOOGLE_API_KEY` | `GOOGLE_API_BASE` |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API_BASE` |
| Moonshot | `MOONSHOT_API_KEY` | `MOONSHOT_API_BASE` |
| DashScope | `DASHSCOPE_API_KEY` | `DASHSCOPE_API_BASE` |
| Azure | `AZURE_OPENAI_API_KEY` | `AZURE_OPENAI_API_BASE` |
| Ollama | - | `OLLAMA_API_BASE` |

### 搜索工具

| 工具 | API Key 变量 |
| :--- | :--- |
| Tavily | `TAVILY_API_KEY` |
| Brave | `BRAVE_API_KEY` |

### 通用配置

| 变量名 | 对应配置项 | 示例 |
| :--- | :--- | :--- |
| `FINCHBOT_LANGUAGE` | `language` | `zh-CN` |
| `FINCHBOT_DEFAULT_MODEL` | `default_model` | `gpt-4-turbo` |
| `FINCHBOT_WORKSPACE` | `agents.defaults.workspace` | `/path/to/workspace` |

---

## 3. 完整配置示例 (`config.json`)

```json
{
  "language": "zh-CN",
  "default_model": "gpt-4o",
  "agents": {
    "defaults": {
      "workspace": "D:/FinchBotWorkspace",
      "temperature": 0.5,
      "max_tool_iterations": 20
    }
  },
  "providers": {
    "openai": {
      "api_key": "sk-proj-...",
      "api_base": "https://api.openai-proxy.com/v1"
    }
  },
  "tools": {
    "restrict_to_workspace": true,
    "web": {
      "search": {
        "max_results": 10
      }
    },
    "exec": {
      "timeout": 120
    }
  }
}
```
