# 使用指南

FinchBot 提供了丰富的命令行界面 (CLI) 来与智能体进行交互。本文档详细介绍所有可用的命令和交互方式。

## 快速开始：三步上手

```bash
# 第一步：配置 API 密钥和默认模型
uv run finchbot config

# 第二步：管理你的会话
uv run finchbot sessions

# 第三步：开始对话
uv run finchbot chat
```

这三个命令覆盖了 FinchBot 的核心工作流程：

| 命令 | 功能 | 说明 |
|------|------|------|
| `finchbot config` | 交互式配置 | 配置 LLM 提供商、API 密钥、默认模型、网页搜索等 |
| `finchbot sessions` | 会话管理 | 全屏界面创建、重命名、删除会话，查看会话历史 |
| `finchbot chat` | 开始对话 | 启动交互式聊天，自动加载最近活跃的会话 |

---

## 1. 启动与基本交互

### 启动 FinchBot

```bash
finchbot chat
```

或者使用 `uv run`：

```bash
uv run finchbot chat
```

### 指定会话

您可以指定一个会话 ID 来继续之前的对话或开始新对话：

```bash
finchbot chat --session "project-alpha"
```

如果未指定，系统会自动加载最近一次活跃的会话。

### 指定模型

```bash
finchbot chat --model "gpt-4o"
```

### 指定工作目录

```bash
finchbot chat --workspace "~/my-project"
```

### 交互模式

进入聊天界面后，您可以直接输入自然语言与 Agent 对话。

- **输入**: 直接输入文字并回车。
- **换行**: 目前 CLI 为单行输入模式，长文本建议分段发送或使用文件读取工具。
- **退出**: 输入 `exit`, `quit`, `:q` 或 `q` 退出程序。

---

## 2. 聊天命令 (Slash Commands)

在聊天界面中，以 `/` 开头的输入被视为特殊命令。

### `/history`

查看当前会话的历史消息记录。

- **功能**: 显示从会话开始至今的所有消息（用户、AI、工具调用）。
- **用途**: 回顾上下文，或查看消息索引（用于回滚）。

**示例输出**:

```
─── 第 1 轮对话 ───
┌─────────────────────────────────┐
│ 👤 你                           │
│ 你好，请记住我的邮箱是 test@example.com
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ 🐦 FinchBot                     │
│ 好的，我已经记住了您的邮箱地址。  │
└─────────────────────────────────┘
```

### `/rollback <index> [new_session_id]`

时光倒流：将对话状态回滚到指定的消息索引处。

- **参数**:
    - `<index>`: 目标消息的索引号（可通过 `/history` 查看）。
    - `[new_session_id]` (可选): 如果提供，将创建一个新的分支会话，原会话保持不变。如果不提供，将覆盖当前会话。
- **示例**:
    - `/rollback 5`: 回滚到第 5 条消息之后的状态（删除索引 > 5 的所有消息）。
    - `/rollback 5 branch-b`: 基于第 5 条消息的状态创建名为 `branch-b` 的新会话。

**使用场景**:
- 修正错误方向：当对话走向偏离预期时回退
- 探索分支：创建新会话尝试不同的对话路径

### `/back <n>`

撤销最近的 n 条消息。

- **参数**:
    - `<n>`: 要撤销的消息数量。
- **示例**:
    - `/back 1`: 撤销最后一条消息（通常用于纠正刚才发错的内容）。
    - `/back 2`: 撤销最后的一轮对话（用户提问 + AI 回复）。

---

## 3. 会话管理界面

FinchBot 提供了一个全屏的交互式会话管理器。

### 进入管理器

直接运行会话管理命令：

```bash
finchbot sessions
```

或者不带任何参数启动 `finchbot chat`，且没有历史会话时，也会自动进入。

### 操作指南

| 按键 | 功能 |
|------|------|
| ↑ / ↓ | 导航选择会话 |
| Enter | 进入选中的会话 |
| r | 重命名当前选中的会话 |
| d | 删除当前选中的会话 |
| n | 创建新会话 |
| q | 退出管理器 |

### 会话信息显示

会话列表会显示以下信息：

| 列 | 说明 |
|----|------|
| ID | 会话唯一标识 |
| 标题 | 会话标题（自动生成或手动设置） |
| 消息数 | 会话中的消息总数 |
| 会话轮次 | 问答轮次数量 |
| 创建时间 | 会话创建的时间 |
| 最后活跃 | 最后一次交互的时间 |

---

## 4. 配置管理器

FinchBot 提供了交互式配置管理界面。

### 进入配置管理器

```bash
finchbot config
```

这将启动交互式界面，用于配置：

### 配置项

| 配置项 | 说明 |
|--------|------|
| 语言 | 界面语言（中文/英文） |
| LLM 提供商 | OpenAI、Anthropic、DeepSeek 等 |
| API 密钥 | 各提供商的 API Key |
| API Base URL | 自定义 API 端点（可选） |
| 默认模型 | 默认使用的聊天模型 |
| 网页搜索 | Tavily / Brave Search API Key |

### 支持的 LLM 提供商

| 提供商 | 说明 |
|--------|------|
| OpenAI | GPT-5, GPT-5.2, O3-mini |
| Anthropic | Claude Sonnet 4.5, Claude Opus 4.6 |
| DeepSeek | DeepSeek Chat, DeepSeek Reasoner |
| DashScope | 阿里云通义千问 (Qwen, QwQ) |
| Groq | Llama 4 Scout/Maverick, Llama 3.3 |
| Moonshot | Kimi K1.5/K2.5 |
| OpenRouter | 多提供商网关 |
| Google Gemini | Gemini 2.5 Flash |

### 环境变量配置

也可以通过环境变量配置：

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_API_BASE="https://api.openai.com/v1"  # 可选

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."

# Tavily (网页搜索)
export TAVILY_API_KEY="tvly-..."
```

---

## 5. 模型管理

### 自动下载

FinchBot 采用**运行时自动下载**机制。

当您首次运行 `finchbot chat` 或其他需要嵌入模型的功能时，系统会自动检测模型是否存在。如果不存在，会自动从最佳镜像源下载到 `.models/fastembed/` 目录。

> **说明**：模型约 95MB，无需手动干预，首次启动时只需等待片刻即可。

### 手动下载

如果您希望提前下载模型（例如在无网环境部署前），可以运行：

```bash
finchbot models download
```

系统会自动检测网络环境并选择最佳的镜像源：
- 国内用户：使用 hf-mirror.com 镜像
- 国外用户：使用 Hugging Face 官方源

**模型信息**：
- 模型名称：`BAAI/bge-small-zh-v1.5`
- 用途：记忆系统的语义检索

---

## 6. 内置工具使用

FinchBot 内置了 11 个工具，分为四大类：

### 文件操作工具

| 工具 | 说明 | 使用场景 |
|------|------|----------|
| `read_file` | 读取文件内容 | 查看代码、配置文件 |
| `write_file` | 写入文件（覆盖） | 创建新文件 |
| `edit_file` | 编辑文件（替换） | 修改现有文件的部分内容 |
| `list_dir` | 列出目录内容 | 探索项目结构 |

**最佳实践**：

```
1. 先用 list_dir 了解目录结构
2. 再用 read_file 查看文件内容
3. 根据需求使用 write_file 或 edit_file
```

### 网络工具

| 工具 | 说明 | 使用场景 |
|------|------|----------|
| `web_search` | 搜索互联网 | 获取最新信息、验证事实 |
| `web_extract` | 提取网页内容 | 获取网页全文 |

**搜索引擎优先级**：
1. Tavily（质量最佳，专为 AI 优化）
2. Brave Search（免费额度大，隐私友好）
3. DuckDuckGo（无需 API 密钥，始终可用）

**最佳实践**：

```
1. 先用 web_search 找到相关 URL
2. 再用 web_extract 获取详细内容
```

### 记忆管理工具

| 工具 | 说明 | 使用场景 |
|------|------|----------|
| `remember` | 保存记忆 | 记录用户信息、偏好 |
| `recall` | 检索记忆 | 回忆之前的信息 |
| `forget` | 删除记忆 | 清除过期或错误信息 |

#### 记忆分类

| 分类 | 说明 | 示例 |
|------|------|------|
| personal | 个人信息 | 姓名、年龄、住址 |
| preference | 用户偏好 | 喜好、习惯 |
| work | 工作相关 | 项目、任务、会议 |
| contact | 联系方式 | 邮箱、电话 |
| goal | 目标计划 | 愿望、计划 |
| schedule | 日程安排 | 时间、提醒 |
| general | 通用 | 其他信息 |

#### 检索策略 (QueryType)

| 策略 | 权重 | 使用场景 |
|------|------|----------|
| `factual` | 关键词 0.8 / 语义 0.2 | "我的邮箱是多少" |
| `conceptual` | 关键词 0.2 / 语义 0.8 | "我喜欢的食物" |
| `complex` | 关键词 0.5 / 语义 0.5 | 复杂查询（默认） |
| `ambiguous` | 关键词 0.3 / 语义 0.7 | 歧义查询 |
| `keyword_only` | 关键词 1.0 / 语义 0.0 | 精确匹配 |
| `semantic_only` | 关键词 0.0 / 语义 1.0 | 语义探索 |

### 系统工具

| 工具 | 说明 | 使用场景 |
|------|------|----------|
| `exec` | 执行 shell 命令 | 批量操作、系统命令 |
| `session_title` | 管理会话标题 | 获取/设置会话标题 |

---

## 7. Bootstrap 文件系统

FinchBot 使用可编辑的 Bootstrap 文件系统来定义 Agent 的行为。这些文件位于工作目录下，用户可以随时编辑。

### Bootstrap 文件

| 文件 | 说明 |
|------|------|
| `SYSTEM.md` | 系统提示词，定义 Agent 的基本行为 |
| `MEMORY_GUIDE.md` | 记忆系统使用指南 |
| `SOUL.md` | Agent 的自我认知和性格特征 |
| `AGENT_CONFIG.md` | Agent 配置（温度、最大令牌等） |

### 编辑 Bootstrap 文件

您可以直接编辑这些文件来自定义 Agent 行为：

```bash
# 查看当前工作目录
finchbot chat --workspace "~/my-workspace"

# 编辑系统提示词
# 文件位置: ~/my-workspace/SYSTEM.md
```

**示例 - 自定义 SYSTEM.md**：

```markdown
# FinchBot (雀翎)

你是一个专业的代码助手，专注于 Python 开发。

## 角色定位
你是 FinchBot，一个专业的 Python 开发助手。

## 专长领域
- Python 3.13+ 特性
- 异步编程 (asyncio)
- 类型提示 (type hints)
- 测试驱动开发 (TDD)
```

---

## 8. 全局选项

`finchbot` 命令行支持以下全局选项：

| 选项 | 说明 |
|------|------|
| `--help` | 显示帮助信息 |
| `--version` | 显示版本号 |
| `-v` | 显示 INFO 及以上日志 |
| `-vv` | 显示 DEBUG 及以上日志（调试模式） |

**示例**:

```bash
# 显示 INFO 级别日志
finchbot chat -v

# 显示 DEBUG 级别日志，查看详细的思维过程和网络请求
finchbot chat -vv
```

---

## 9. 命令速查表

| 命令 | 说明 |
|------|------|
| `finchbot chat` | 启动交互式聊天会话 |
| `finchbot chat -s <id>` | 启动/继续指定会话 |
| `finchbot chat -m <model>` | 使用指定模型 |
| `finchbot chat -w <dir>` | 使用指定工作目录 |
| `finchbot sessions` | 打开会话管理器 |
| `finchbot config` | 打开配置管理器 |
| `finchbot models download` | 下载嵌入模型 |
| `finchbot version` | 显示版本信息 |

---

## 10. 聊天命令速查表

| 命令 | 说明 |
|------|------|
| `/history` | 显示会话历史（带索引） |
| `/rollback <n>` | 回滚到第 n 条消息 |
| `/rollback <n> <new_id>` | 创建分支会话 |
| `/back <n>` | 撤销最近 n 条消息 |
| `exit` / `quit` / `q` | 退出聊天 |
