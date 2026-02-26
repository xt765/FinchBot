# 

FinchBot  ****  **** 

******** > **** (`~/.finchbot/config.json`) > ****

## 

1. [](#1-)
2. [](#2-)
3. [](#3-)
4. [](#4-)
5. [](#5-)

---

## 1. 

 `~/.finchbot/config.json`

### 

|  |  |  |  |
| :--- | :--- | :--- | :--- |
| `language` | string | `"en-US"` |  `zh-CN`, `zh-HK`, `en-US` |
| `language_set_by_user` | boolean | `false` |  |
| `default_model` | string | `"gpt-5"` |  LLM  |
| `default_model_set_by_user` | boolean | `false` |  |
| `agents` | object | - | Agent  |
| `providers` | object | - | LLM  |
| `tools` | object | - |  |

### `agents` 

|  |  |  |  |
| :--- | :--- | :--- | :--- |
| `defaults.workspace` | string | `~/.finchbot/workspace` | Agent  |
| `defaults.model` | string | `"gpt-5"` |  |
| `defaults.temperature` | float | `0.7` |  (0.0-1.0)0.0 1.0  |
| `defaults.max_tokens` | int | `8192` |  Token  |
| `defaults.max_tool_iterations` | int | `20` |  |

### `providers` 

`openai`, `anthropic`, `gemini`, `deepseek`, `moonshot`, `dashscope`, `groq`, `openrouter`, `custom`



|  |  |  |
| :--- | :--- | :--- |
| `api_key` | string | API  |
| `api_base` | string | API  URL |
| `extra_headers` | dict |  |
| `models` | list[str] |  |
| `openai_compatible` | bool |  OpenAI API true |

****

|  |  |  |  |
| :--- | :--- | :--- | :--- |
| `openai` | OpenAI  | `OPENAI_*` | gpt-5, gpt-5.2, o3-mini |
| `anthropic` | Anthropic Claude | `ANTHROPIC_*` | claude-sonnet-4.5, claude-opus-4.6 |
| `gemini` | Google Gemini | `GOOGLE_*` | gemini-2.5-flash |
| `deepseek` | DeepSeek | `DEEPSEEK_*` | deepseek-chat, deepseek-reasoner |
| `moonshot` | Moonshot (Kimi) | `MOONSHOT_*` | kimi-k1.5, kimi-k2.5 |
| `dashscope` |  | `DASHSCOPE_*` | qwen-turbo, qwen-max |
| `groq` | Groq | `GROQ_*` | llama-4-scout, llama-4-maverick |
| `openrouter` | OpenRouter | `OPENROUTER_*` | () |
| `custom` |  |  | - |

### `tools` 

|  |  |  |  |
| :--- | :--- | :--- | :--- |
| `restrict_to_workspace` | bool | `false` |  |
| `web.search.max_results` | int | `5` |  |
| `web.search.api_key` | string | - | Tavily  API Key |
| `web.search.brave_api_key` | string | - | Brave  API Key |
| `exec.timeout` | int | `60` | Shell  |

---

## 2. 

 `FINCHBOT_` 

 `__` Pydantic Settings 

### LLM 

|  | API Key  | API Base  |
| :--- | :--- | :--- |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_API_BASE` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_BASE` |
| Gemini | `GOOGLE_API_KEY` | - |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API_BASE` |
| Groq | `GROQ_API_KEY` | `GROQ_API_BASE` |
| Moonshot | `MOONSHOT_API_KEY` | `MOONSHOT_API_BASE` |
| DashScope | `DASHSCOPE_API_KEY` | `DASHSCOPE_API_BASE` |
| OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_API_BASE` |

### 

|  | API Key  |  |
| :--- | :--- | :--- |
| Tavily | `TAVILY_API_KEY` |  API Key |
| Brave | `BRAVE_API_KEY` |  API Key |
| DuckDuckGo | - |  API Key () |

### 

|  |  |  |
| :--- | :--- | :--- |
| `FINCHBOT_LANGUAGE` | `language` | `zh-CN` |
| `FINCHBOT_DEFAULT_MODEL` | `default_model` | `gpt-4o` |
| `FINCHBOT_AGENTS__DEFAULTS__WORKSPACE` | `agents.defaults.workspace` | `/path/to/workspace` |
| `FINCHBOT_TOOLS__RESTRICT_TO_WORKSPACE` | `tools.restrict_to_workspace` | `true` |

---

## 3. 

### 



```bash
uv run finchbot config
```


- 
- 
-  API Key 
- 

### 

1.  
2.   `~/.finchbot/config.json`

### 

 `.env` 

```bash
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
FINCHBOT_LANGUAGE=zh-CN
FINCHBOT_DEFAULT_MODEL=gpt-5
```

---

## 4. 

### 

```json
{
  "language": "zh-CN",
  "default_model": "gpt-5",
  "providers": {
    "openai": {
      "api_key": "sk-proj-..."
    }
  }
}
```

### 

```json
{
  "language": "zh-CN",
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

###  DeepSeek 

```json
{
  "language": "zh-CN",
  "default_model": "deepseek-chat",
  "providers": {
    "deepseek": {
      "api_key": "sk-...",
      "api_base": "https://api.deepseek.com"
    }
  }
}
```

###  Ollama 

```json
{
  "language": "zh-CN",
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

## 5. 

### Bootstrap 

FinchBot  Agent 

```
~/.finchbot/
 config.json         # 
 SYSTEM.md           # 
 MEMORY_GUIDE.md     # 
 SOUL.md             # 
 AGENT_CONFIG.md     # Agent 
 workspace/
     checkpoints.db  # 
     memories.db     # 
     chroma/         # 
     skills/         # 
         my-skill/
             SKILL.md
```

###  SYSTEM.md

```markdown
# 

 AI  FinchBot

## 
- 
- 
- 
- 

## 
- 
- 
- 
```

###  SOUL.md

```markdown
# 

## 
- 
- 
- 

## 
- 
- 
- 
```

### 



```bash
# WARNING 
finchbot chat

# INFO 
finchbot -v chat

# DEBUG 
finchbot -vv chat
```

---

## 



```bash
uv run finchbot config
```



```bash
uv run finchbot chat
```

---

## 

| / |  |  |
| :--- | :--- | :--- |
|  | `~/.finchbot/config.json` |  |
|  |  `.env` |  |
|  | `~/.finchbot/workspace/` |  |
|  | `~/.finchbot/workspace/memories.db` | SQLite  |
|  | `~/.finchbot/workspace/chroma/` | ChromaDB |
|  | `~/.finchbot/workspace/checkpoints.db` | LangGraph  |
