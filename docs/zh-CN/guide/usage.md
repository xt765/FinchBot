# 使用指南

FinchBot 提供了丰富的命令行界面（CLI）用于与 Agent 交互。本文档详细介绍所有可用命令和交互模式。

## 快速开始：三步上手

```bash
# 第一步：配置 API Key 和默认模型
uv run finchbot config

# 第二步：管理会话
uv run finchbot sessions

# 第三步：开始聊天
uv run finchbot chat
```

这三个命令覆盖了 FinchBot 的核心工作流：

```mermaid
flowchart LR
    classDef step fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1,rx:10,ry:10;

    A["1. finchbot config<br/>配置 API Key"]:::step --> B["2. finchbot sessions<br/>管理会话"]:::step
    B --> C["3. finchbot chat<br/>开始聊天"]:::step
```

| 命令 | 功能 | 说明 |
| :--- | :--- | :--- |
| `finchbot config` | 交互式配置 | 配置 LLM 提供商、API Key、默认模型、网页搜索等 |
| `finchbot sessions` | 会话管理 | 全屏界面，创建、重命名、删除会话，查看历史 |
| `finchbot chat` | 开始对话 | 启动交互式聊天，自动加载上次活动会话 |

---

## 1. 启动与基本交互

### 1.1 CLI 界面

#### 启动 FinchBot

```bash
finchbot chat
```

或使用 `uv run`：

```bash
uv run finchbot chat
```

#### 指定会话

可以指定会话 ID 继续之前的对话或开始新会话：

```bash
finchbot chat --session "project-alpha"
```

#### 指定模型

```bash
finchbot chat --model "gpt-5"
```

### 1.2 Web 界面（Beta）

FinchBot 现已支持现代化的 Web 界面。

```mermaid
flowchart TB
    classDef backend fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef frontend fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef user fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    subgraph Backend [后端服务]
        API[FastAPI<br/>:8000]:::backend
        WS[WebSocket<br/>实时通信]:::backend
    end

    subgraph Frontend [前端界面]
        React[React + Vite<br/>:5173]:::frontend
        MD[Markdown 渲染]:::frontend
    end

    U[用户]:::user --> React
    React <--> WS
    WS <--> API

    API --> React
    React --> MD
    MD --> U
```

#### 启动后端服务

```bash
uv run finchbot serve
```

服务将在 `http://127.0.0.1:8000` 启动。

#### 启动前端界面

```bash
cd web
npm install
npm run dev
```

在浏览器中打开 `http://localhost:5173` 即可开始聊天。

Web 界面特性：
- 实时流式输出
- Markdown 富文本渲染
- 代码高亮
- 自动加载历史

---

## 2. 斜杠命令

在聊天界面中，以 `/` 开头的输入被视为特殊命令。

### `/history`

查看当前会话的历史消息。

- **功能**：显示会话开始以来的所有消息（用户、AI、工具调用）。
- **用途**：回顾上下文或检查消息索引（用于回滚）。

**示例输出**：

```
 Turn 1 

  你                          
 你好，请记住我的邮箱是 test@example.com


  FinchBot                     
 我已保存你的邮箱地址。

```

### `/rollback <index> [new_session_id]`

时光机：将对话状态回滚到指定消息索引。

- **参数**：
    - `<index>`：目标消息索引（通过 `/history` 查看）。
    - `[new_session_id]`（可选）：如果提供，将创建新的分支会话，保留原会话。如果不提供，则覆盖当前会话。
- **示例**：
    - `/rollback 5`：回滚到消息 5 之后的状态（删除所有索引 > 5 的消息）。
    - `/rollback 5 branch-b`：基于消息 5 的状态创建新会话 `branch-b`。

**使用场景**：
- 纠正错误方向：对话偏离时回滚
- 探索分支：创建新会话尝试不同的对话路径

### `/back <n>`

撤销最近 n 条消息。

- **参数**：
    - `<n>`：要撤销的消息数量。
- **示例**：
    - `/back 1`：撤销最后一条消息（适合纠正输入错误）。
    - `/back 2`：撤销最后一轮对话（用户提问 + AI 回复）。

---

## 3. 会话管理器

FinchBot 提供全屏交互式会话管理器。

### 进入管理器

直接运行 sessions 命令：

```bash
finchbot sessions
```

或在无历史会话时直接启动 `finchbot chat`。

### 操作按键

| 按键 | 操作 |
| :--- | :--- |
| ↑ / ↓ | 导航会话 |
| Enter | 进入选中会话 |
| r | 重命名选中会话 |
| d | 删除选中会话 |
| n | 创建新会话 |
| q | 退出管理器 |

### 会话信息显示

会话列表显示以下信息：

| 列 | 说明 |
| :--- | :--- |
| ID | 会话唯一标识 |
| Title | 会话标题（自动生成或手动设置） |
| Messages | 会话中消息总数 |
| Turns | 对话轮数 |
| Created | 会话创建时间 |
| Last Active | 最后交互时间 |

---

## 4. 配置管理器

FinchBot 提供交互式配置管理器。

### 进入配置管理器

```bash
finchbot config
```

这将启动交互式界面来配置：

### 配置选项

| 选项 | 说明 |
| :--- | :--- |
| 语言 | 界面语言（中文/英文） |
| LLM 提供商 | OpenAI、Anthropic、DeepSeek 等 |
| API Key | 各提供商的 API Key |
| API Base URL | 自定义 API 端点（可选） |
| 默认模型 | 默认使用的聊天模型 |
| 网页搜索 | Tavily / Brave Search API Key |

### 支持的 LLM 提供商

| 提供商 | 说明 |
| :--- | :--- |
| OpenAI | GPT-5、GPT-5.2、O3-mini |
| Anthropic | Claude Sonnet 4.5、Claude Opus 4.6 |
| DeepSeek | DeepSeek Chat、DeepSeek Reasoner |
| DashScope | 阿里云通义千问、QwQ |
| Groq | Llama 4 Scout/Maverick、Llama 3.3 |
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

# Tavily（网页搜索）
export TAVILY_API_KEY="tvly-..."
```

---

## 5. 模型管理

### 自动下载

FinchBot 采用**运行时自动下载**机制。

首次运行 `finchbot chat` 或其他需要嵌入模型的功能时，系统会自动检查模型。如果缺失，将从最佳镜像源自动下载到 `.models/fastembed/` 目录。

> **注意**：模型约 95MB。无需手动干预，首次启动时稍等片刻即可。

### 手动下载

如需提前下载模型（例如部署到离线环境前），可运行：

```bash
finchbot models download
```

系统会自动检测网络环境并选择最佳镜像源：
- 国内用户：使用 hf-mirror.com 镜像
- 国际用户：使用 Hugging Face 官方源

**模型信息**：
- 模型名称：`BAAI/bge-small-zh-v1.5`
- 用途：记忆系统的语义检索

---

## 6. 内置工具使用

FinchBot 包含 11 个内置工具，分为四大类：

```mermaid
flowchart TB
    classDef category fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef tool fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    subgraph Tools [11 个内置工具]
        File[文件操作]:::category
        Web[网络]:::category
        Memory[记忆]:::category
        System[系统]:::category
    end

    File --> F1[read_file]:::tool
    File --> F2[write_file]:::tool
    File --> F3[edit_file]:::tool
    File --> F4[list_dir]:::tool

    Web --> W1[web_search]:::tool
    Web --> W2[web_extract]:::tool

    Memory --> M1[remember]:::tool
    Memory --> M2[recall]:::tool
    Memory --> M3[forget]:::tool

    System --> S1[exec]:::tool
    System --> S2[session_title]:::tool
```

### 文件操作工具

| 工具 | 说明 | 使用场景 |
| :--- | :--- | :--- |
| `read_file` | 读取文件内容 | 查看代码、配置文件 |
| `write_file` | 写入文件（覆盖） | 创建新文件 |
| `edit_file` | 编辑文件（替换） | 修改现有文件的特定部分 |
| `list_dir` | 列出目录内容 | 探索项目结构 |

**最佳实践**：

```
1. 使用 list_dir 了解目录结构
2. 使用 read_file 查看文件内容
3. 根据需要使用 write_file 或 edit_file
```

### 网络工具

| 工具 | 说明 | 使用场景 |
| :--- | :--- | :--- |
| `web_search` | 搜索互联网 | 获取最新信息、验证事实 |
| `web_extract` | 提取网页内容 | 获取完整网页内容 |

**搜索引擎优先级**：
1. Tavily（质量最佳，专为 AI 优化）
2. Brave Search（免费额度大，隐私友好）
3. DuckDuckGo（无需 API Key，始终可用）

**最佳实践**：

```
1. 使用 web_search 查找相关 URL
2. 使用 web_extract 获取详细内容
```

### 记忆管理工具

| 工具 | 说明 | 使用场景 |
| :--- | :--- | :--- |
| `remember` | 保存记忆 | 记录用户信息、偏好 |
| `recall` | 检索记忆 | 回忆之前的信息 |
| `forget` | 删除记忆 | 清除过时或错误信息 |

#### 记忆分类

| 分类 | 说明 | 示例 |
| :--- | :--- | :--- |
| personal | 个人信息 | 姓名、年龄、地址 |
| preference | 用户偏好 | 喜好、习惯 |
| work | 工作相关 | 项目、任务、会议 |
| contact | 联系方式 | 邮箱、电话 |
| goal | 目标计划 | 愿望、计划 |
| schedule | 日程安排 | 时间、提醒 |
| general | 一般信息 | 其他信息 |

#### 检索策略（QueryType）

| 策略 | 权重 | 使用场景 |
| :--- | :--- | :--- |
| `factual` | 关键词 0.8 / 语义 0.2 | "我的邮箱是什么" |
| `conceptual` | 关键词 0.2 / 语义 0.8 | "我喜欢什么食物" |
| `complex` | 关键词 0.5 / 语义 0.5 | 复杂查询（默认） |
| `ambiguous` | 关键词 0.3 / 语义 0.7 | 歧义查询 |
| `keyword_only` | 关键词 1.0 / 语义 0.0 | 精确匹配 |
| `semantic_only` | 关键词 0.0 / 语义 1.0 | 语义探索 |

### 系统工具

| 工具 | 说明 | 使用场景 |
| :--- | :--- | :--- |
| `exec` | 执行 Shell 命令 | 批量操作、系统命令 |
| `session_title` | 管理会话标题 | 获取/设置会话标题 |

---

## 7. Bootstrap 文件系统

FinchBot 使用可编辑的 Bootstrap 文件系统来定义 Agent 行为。这些文件位于工作区目录，可随时编辑。

### Bootstrap 文件

| 文件 | 说明 |
| :--- | :--- |
| `SYSTEM.md` | 系统提示词，定义 Agent 基本行为 |
| `MEMORY_GUIDE.md` | 记忆系统使用指南 |
| `SOUL.md` | Agent 自我认知和性格特征 |
| `AGENT_CONFIG.md` | Agent 配置（温度、最大令牌等） |

### 编辑 Bootstrap 文件

可以直接编辑这些文件来自定义 Agent 行为：

```bash
# 查看当前工作区
finchbot chat --workspace "~/my-workspace"

# 编辑系统提示词
# 文件位置：~/my-workspace/SYSTEM.md
```

**示例 - 自定义 SYSTEM.md**：

```markdown
# FinchBot

你是一个专注于 Python 开发的专业代码助手。

## 角色
你是 FinchBot，一个专业的 Python 开发助手。

## 专长
- Python 3.13+ 新特性
- 异步编程（asyncio）
- 类型注解
- 测试驱动开发（TDD）
```

---

## 8. 全局选项

`finchbot` 命令支持以下全局选项：

| 选项 | 说明 |
| :--- | :--- |
| `--help` | 显示帮助信息 |
| `--version` | 显示版本号 |
| `-v` | 显示 INFO 及以上日志 |
| `-vv` | 显示 DEBUG 及以上日志（调试模式） |

**示例**：

```bash
# 显示 INFO 级别日志
finchbot chat -v

# 显示 DEBUG 级别日志，查看详细思考过程和网络请求
finchbot chat -vv
```

---

## 9. 命令参考

| 命令 | 说明 |
| :--- | :--- |
| `finchbot chat` | 启动交互式聊天会话 |
| `finchbot chat -s <id>` | 启动/继续指定会话 |
| `finchbot chat -m <model>` | 使用指定模型 |
| `finchbot chat -w <dir>` | 使用指定工作区 |
| `finchbot sessions` | 打开会话管理器 |
| `finchbot config` | 打开配置管理器 |
| `finchbot models download` | 下载嵌入模型 |
| `finchbot version` | 显示版本信息 |

---

## 10. 聊天命令参考

| 命令 | 说明 |
| :--- | :--- |
| `/history` | 显示会话历史（含索引） |
| `/rollback <n>` | 回滚到消息 n |
| `/rollback <n> <new_id>` | 创建分支会话 |
| `/back <n>` | 撤销最近 n 条消息 |
| `exit` / `quit` / `q` | 退出聊天 |
