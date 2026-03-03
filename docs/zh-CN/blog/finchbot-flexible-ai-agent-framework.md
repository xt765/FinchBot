
<div align="center"> 
  <img src="https://i-blog.csdnimg.cn/direct/8abea218c2804256a17cc8f2d6c81630.jpeg" width="150" > 
  <h1><strong>玄同 765</strong></h1> 
  <p><strong>大语言模型 (LLM) 开发工程师 | 中国传媒大学 · 数字媒体技术（智能交互与游戏设计）</strong></p> 
  <p> 
    <a href="https://blog.csdn.net/Yunyi_Chi" target="_blank" style="text-decoration: none;"> 
      <span style="background-color: #f39c12; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block;">CSDN · 个人主页 |</span> 
    </a> 
    <a href="https://github.com/xt765" target="_blank" style="text-decoration: none; margin-left: 8px;"> 
      <span style="background-color: #24292e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block;">GitHub · Follow</span> 
    </a> 
  </p> 
</div> 

--- 

### **关于作者** 

- **深耕领域**：大语言模型开发 / RAG 知识库 / AI Agent 落地 / 模型微调 
- **技术栈**：Python | RAG (LangChain / Dify + Milvus) | FastAPI + Docker 
- **工程能力**：专注模型工程化部署、知识库构建与优化，擅长全流程解决方案 

> **「让 AI 交互更智能，让技术落地更高效」** 
> 欢迎技术探讨与项目合作，解锁大模型与智能交互的无限可能！

---

# FinchBot (雀翎) — 当 AI 说"让我想办法"而不是"我不会"

<p align="center"> 
   <img src="https://i-blog.csdnimg.cn/direct/60cd5e5971cc4226977289a17a99dbae.png" alt="FinchBot Logo" width="600"> 
 </p>

<p align="center">
  <em>基于 LangChain v1.2 与 LangGraph v1.0 构建<br>
  具备持久记忆、动态提示词、自主能力扩展</em>
</p>

**🎉 Gitee 官方推荐项目** — FinchBot 已获得 Gitee 官方推荐！



> **项目地址**：[GitHub - FinchBot](https://github.com/xt765/FinchBot) | [Gitee - FinchBot](https://gitee.com/xt765/FinchBot)
> **文档**：[FinchBot 文档](https://github.com/xt765/FinchBot/tree/main/docs)
> **问题反馈**：[GitHub Issues](https://github.com/xt765/FinchBot/issues)

---

## 摘要


*想象这样一个对话：*

> **用户**："帮我分析这个 SQLite 数据库"
><br> **传统 AI**："抱歉，我没有数据库操作的能力，无法完成这个任务。"<br>
> **FinchBot**：*[思考：我还没有数据库工具...]* 
> "让我配置一下数据库工具。" 
> *[调用 configure_mcp 添加 SQLite MCP]* 
> *[新工具已加载：query_sqlite, list_tables...]* 
> "好了！现在可以分析你的数据库了。数据库包含 3 张表..."

**这就是 FinchBot 的核心差异**：遇到能力边界时，不是"放弃"，而是"想办法"。

基于 **LangChain v1.2** 和 **LangGraph v1.0**，FinchBot 赋予智能体真正的自主性：

1. **能力自扩展** — Agent 遇到能力边界时，可使用内置工具配置 MCP、创建技能
2. **任务自调度** — Agent 可自主设定后台任务、定时执行，不阻塞对话
3. **记忆自管理** — Agent 可自主记忆、检索、遗忘，Agentic RAG + 加权 RRF 混合检索，智能召回
4. **行为自进化** — Agent 和用户都可自主修改提示词，持续迭代优化行为

---

## 能力边界问题

| 用户请求 | 传统 AI 回应 | FinchBot 回应 |
|:---|:---|:---|
| "分析这个数据库" | "我没有数据库工具" | 自主配置 SQLite MCP，然后分析 |
| "学会做某事" | "等开发者添加功能" | 通过 skill-creator 自主创建技能 |
| "帮我监控 24 小时" | "我只能在你问的时候响应" | 创建定时任务，自主监控 |
| "处理这个大文件" | 阻塞对话，用户等待 | 后台执行，用户继续 |
| "记住我的偏好" | "下次对话就忘了" | 持久记忆，Agentic RAG + 加权 RRF 混合检索 |
| "调整你的行为" | "提示词是固定的" | 动态修改提示词，热加载 |

---
## 系统架构

**核心理念**：FinchBot 智能体不只是响应 — 它们自主执行、自主规划、自主扩展。

### 自主性金字塔

```mermaid
flowchart TB
    subgraph L4["扩展层 - 自主扩展能力"]
        E1["MCP 自动配置"] ~~~ E2["技能创建"] ~~~ E3["动态加载"]
    end

    subgraph L3["规划层 - 自主创建计划"]
        P1["定时任务"] ~~~ P2["心跳监控"] ~~~ P3["自动触发"]
    end

    subgraph L2["执行层 - 自主执行任务"]
        X1["后台任务"] ~~~ X2["异步处理"] ~~~ X3["非阻塞"]
    end

    subgraph L1["响应层 - 响应用户请求"]
        R1["对话系统"] ~~~ R2["工具调用"] ~~~ R3["上下文记忆"]
    end

    L4 --> L3 --> L2 --> L1

    style L1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20
    style L2 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1
    style L3 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c
    style L4 fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#f57f17
```

| 层级 | 能力 | 实现方式 | 用户价值 |
|:---:|:---|:---|:---|
| **响应层** | 响应用户请求 | 对话系统 + 工具调用 | 基础交互 |
| **执行层** | 自主执行任务 | 后台任务系统 | 对话不阻塞 |
| **规划层** | 自主创建计划 | 定时任务 + 心跳服务 | 自动化执行 |
| **扩展层** | 自主扩展能力 | MCP 配置 + 技能创建 | 无限扩展 |

### 整体架构

```mermaid
flowchart TB
    subgraph Input [输入层]
        direction LR
        CLI[CLI 界面<br/>Rich 美化]
        LB[LangBot<br/>12+ 平台]
        Webhook[Webhook<br/>FastAPI]
    end

    subgraph Core [核心层 - Agent 决策引擎]
        direction TB
        Agent[LangGraph Agent<br/>状态管理 · 循环控制]
        subgraph CoreModules [核心组件]
            direction LR
            Context[ContextBuilder<br/>上下文构建]
            Streaming[ProgressReporter<br/>流式输出]
        end
    end

    subgraph Capabilities [能力层 - 三层扩展]
        direction LR
        BuiltIn[内置工具<br/>19 个开箱即用]
        MCP[MCP 扩展<br/>动态配置]
        Skills[技能系统<br/>自主创建]
    end

    subgraph Task [任务层 - 三层调度]
        direction LR
        BG[后台任务<br/>异步执行]
        Cron[定时任务<br/>at/every/cron]
        Heart[心跳监控<br/>自主唤醒]
    end

    subgraph Service [服务层 - 统一管理]
        SM[ServiceManager<br/>协调所有后台服务]
    end

    subgraph Memory [记忆层 - 双层存储]
        direction LR
        SQLite[(SQLite<br/>结构化存储)]
        Vector[(VectorStore<br/>向量检索)]
    end

    subgraph LLM [模型层 - 多提供商]
        direction LR
        OpenAI[OpenAI<br/>GPT-4o]
        Anthropic[Anthropic<br/>Claude]
        DeepSeek[DeepSeek<br/>国产]
    end

    CLI --> Agent
    LB <--> Webhook
    Webhook --> Agent

    Agent --> Context
    Agent --> Streaming
    Agent --> Capabilities
    Agent --> Task
    Agent <--> Memory
    Agent --> LLM

    Task --> Service
    Service --> SM

    Context --> Memory
    Memory --> SQLite
    Memory --> Vector
```

### 数据流

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant C as 通道
    participant B as MessageBus
    participant F as AgentFactory
    participant A as Agent
    participant M as MemoryManager
    participant T as 工具
    participant L as LLM

    U->>C: 发送消息
    C->>B: InboundMessage
    B->>F: 获取/创建 Agent
    F->>A: 返回编译后的 Agent
    
    Note over A: 构建上下文
    A->>M: 召回相关记忆
    M-->>A: 返回上下文
    
    A->>L: 发送请求
    L-->>A: 流式响应
    
    alt 需要工具调用
        A->>T: 执行工具
        T-->>A: 返回结果
        A->>L: 继续处理
        L-->>A: 最终响应
    end
    
    A->>M: 存储新记忆
    A->>B: OutboundMessage
    B->>C: 路由到通道
    C->>U: 显示响应
```

### 安全机制

**智能体自主 ≠ 智能体乱来。** FinchBot 实现了多重安全机制：

| 安全机制 | 状态 | 作用 |
|:---|:---:|:---|
| **路径限制** | ✅ 已实现 | 文件操作限定在 workspace 目录内 |
| **Shell 命令黑名单** | ✅ 已实现 | 阻止 `rm -rf`、`format`、`shutdown` 等危险命令 |
| **工具注册机制** | ✅ 已实现 | 只有注册的工具可被调用 |

**理念**：给智能体解决问题的自由，但在明确的边界内。

---

## 核心组件

### 1. 能力自扩展：内置工具 + MCP 配置 + 技能创建

FinchBot 提供三层能力扩展机制，让智能体遇到能力边界时可以自主扩展。

#### 三层扩展机制

```mermaid
flowchart LR
    classDef layer1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef layer2 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef layer3 fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#f57f17;

    L1[第一层<br/>内置工具<br/>开箱即用]:::layer1 --> L2[第二层<br/>MCP 配置<br/>Agent 自主配置]:::layer2 --> L3[第三层<br/>技能创建<br/>Agent 自主创建]:::layer3
```

| 层级 | 方式 | 自主性 | 说明 |
|:---:|:---|:---:|:---|
| 第一层 | 内置工具 | 开箱即用 | 19 个内置工具，无需配置即可使用 |
| 第二层 | MCP 配置 | Agent 自主配置 | 通过 `configure_mcp` 动态添加外部能力 |
| 第三层 | 技能创建 | Agent 自主创建 | 通过 `skill-creator` 创建新技能 |

#### 内置工具

| 类别 | 工具 | 功能 |
| :--- | :--- | :--- |
| **文件操作** | `read_file` | 读取本地文件 |
| | `write_file` | 写入本地文件 |
| | `edit_file` | 编辑文件内容 |
| | `list_dir` | 列出目录内容 |
| **网络能力** | `web_search` | 联网搜索 (Tavily/Brave/DDG) |
| | `web_extract` | 网页内容提取 |
| **记忆管理** | `remember` | 主动存储记忆 |
| | `recall` | 检索记忆 |
| | `forget` | 删除/归档记忆 |
| **系统控制** | `exec` | 安全执行 Shell 命令 |
| **配置管理** | `configure_mcp` | 动态配置 MCP 服务器 |
| | `refresh_capabilities` | 刷新能力描述文件 |
| **后台任务** | `start_background_task` | 启动后台任务 |
| | `check_task_status` | 检查任务状态 |
| | `get_task_result` | 获取任务结果 |
| | `cancel_task` | 取消任务 |
| **定时任务** | `create_cron` | 创建定时任务 |
| | `list_crons` | 列出所有定时任务 |
| | `delete_cron` | 删除定时任务 |

##### 网页搜索

`web_search` 工具采用三引擎降级设计，确保始终可用：

```mermaid
flowchart TD
    Start[网页搜索请求]
    
    Check1{TAVILY_API_KEY<br/>已设置?}
    Tavily[Tavily<br/>质量最佳<br/>AI 优化]
    
    Check2{BRAVE_API_KEY<br/>已设置?}
    Brave[Brave Search<br/>隐私友好<br/>免费额度大]
        
    DDG[DuckDuckGo<br/>零配置<br/>始终可用]

    Start --> Check1
    Check1 -->|是| Tavily
    Check1 -->|否| Check2
    Check2 -->|是| Brave
    Check2 -->|否| DDG
```

| 优先级 | 引擎 | API Key | 特点 |
| :----: | :--- | :-----: | :--- |
| 1 | **Tavily** | 需要 | 质量最佳，专为 AI 优化，深度搜索 |
| 2 | **Brave Search** | 需要 | 免费额度大，隐私友好 |
| 3 | **DuckDuckGo** | 无需 | 始终可用，零配置 |

#### MCP 配置

智能体可通过 `configure_mcp` 工具自主管理 MCP 服务器：

| 操作 | 说明 |
| :--- | :--- |
| `add` | 添加新 MCP 服务器 |
| `update` | 更新现有服务器配置 |
| `remove` | 删除 MCP 服务器 |
| `enable` | 启用已禁用的 MCP 服务器 |
| `disable` | 暂时禁用 MCP 服务器 |
| `list` | 列出所有已配置的服务器 |

**动态能力更新**：

```mermaid
flowchart LR
    MCP[MCP 配置<br/>configure_mcp] --> Refresh[refresh_capabilities] --> Builder[CapabilitiesBuilder<br/>重新生成] --> Write[CAPABILITIES.md] --> Load[下次对话<br/>自动加载]
```

#### 技能创建

FinchBot 内置 **skill-creator** 技能，智能体可自主创建新技能：

```
用户: 帮我创建一个翻译技能，可以把中文翻译成英文

Agent: 好的，我来为你创建翻译技能...
       [调用 skill-creator 技能]
       ✅ 已创建 skills/translator/SKILL.md
       现在你可以直接使用翻译功能了！
```

无需手动创建文件、无需编写代码，**一句话就能扩展 Agent 能力**！

#### 技能文件结构

```
skills/
├── skill-creator/        # 技能创建器（内置）- 开箱即用的核心
│   └── SKILL.md
├── summarize/            # 智能总结（内置）
│   └── SKILL.md
├── weather/              # 天气查询（内置）
│   └── SKILL.md
└── my-custom-skill/      # Agent 自动创建或用户自定义
    └── SKILL.md
```

#### 设计亮点

|           特性           | 说明                              |
| :----------------------: | :-------------------------------- |
| **Agent 自动创建** | 告诉 Agent 需求，自动生成技能文件 |
|   **双层技能源**   | 工作区技能优先，内置技能兜底      |
|    **依赖检查**    | 自动检查 CLI 工具和环境变量       |
|  **缓存失效检测**  | 基于文件修改时间，智能缓存        |
|   **渐进式加载**   | 常驻技能优先，按需加载其他        |

### 2. 任务自调度：后台任务 + 定时任务 + 心跳服务

FinchBot 实现了三层任务调度机制，让智能体能够自主执行、规划和监控任务。

#### 三层调度机制

```mermaid
flowchart TB
    subgraph L3["监控层 - 心跳服务"]
        H1[自主唤醒] ~~~ H2[定期检查] ~~~ H3[主动通知]
    end

    subgraph L2["规划层 - 定时任务"]
        C1[Cron 调度] ~~~ C2[周期执行] ~~~ C3[自动重试]
    end

    subgraph L1["执行层 - 后台任务"]
        B1[异步执行] ~~~ B2[非阻塞] ~~~ B3[结果获取]
    end

    L3 --> L2 --> L1
```

| 层级 | 功能 | 特点 | 使用场景 |
|:---:|:---|:---|:---|
| 执行层 | 后台任务 | 异步执行，不阻塞对话 | 长时间运行的任务 |
| 规划层 | 定时任务 | 周期执行，自动化运行 | 定期提醒、定时报告 |
| 监控层 | 心跳服务 | 主动检查，自主唤醒 | 条件监控、状态追踪 |

#### 后台任务

FinchBot 实现了**四工具模式**用于异步任务执行：

| 工具 | 功能 | 智能体自主性 |
| :--- | :--- | :--- |
| `start_background_task` | 启动后台任务 | 智能体自主判断是否需要后台执行 |
| `check_task_status` | 检查任务状态 | 智能体自主决定何时检查 |
| `get_task_result` | 获取任务结果 | 智能体自主决定何时获取结果 |
| `cancel_task` | 取消任务 | 智能体自主决定是否取消 |

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as 智能体
    participant BG as 后台任务系统
    participant SM as SubagentManager
    participant SA as 子智能体

    U->>A: 执行长任务
    A->>BG: start_background_task
    BG->>SM: 创建 SubagentManager
    SM->>SA: 独立 Agent 循环
    Note over SA: 最多 15 次迭代
    BG-->>A: 返回 job_id
    A-->>U: 任务已启动 (ID: xxx)
    
    Note over U,A: 用户继续对话...
    
    U->>A: 其他问题
    A-->>U: 正常回复
    
    U->>A: 任务进度？
    A->>BG: check_task_status
    BG-->>A: running
    A-->>U: 仍在执行...
    
    SA-->>SM: 任务完成
    SM-->>BG: on_notify 回调
    BG-->>A: 通知结果
    U->>A: 获取结果
    A->>BG: get_task_result
    BG-->>A: 返回结果
    A-->>U: 展示任务结果
```

#### 定时任务

FinchBot 的定时任务系统让智能体能够自主创建和管理周期性任务：

```mermaid
flowchart LR
    Agent[智能体自主创建任务] --> Scheduler[CronService<br/>at/every/cron 三种模式]
    Scheduler --> |触发| Execute[执行任务]
    Execute --> |完成| Notify[on_deliver 回调<br/>通知用户]
    Execute --> |失败| Retry[自动重试]
```

**核心特性**：

| 特性 | 说明 |
| :--- | :--- |
| **三种调度模式** | `at` 指定时间、`every` 周期执行、`cron` 标准 Cron 表达式 |
| **IANA 时区支持** | 支持 `Asia/Shanghai` 等 IANA 时区格式 |
| **on_deliver 回调** | 任务触发时通过回调通知用户 |
| **持久化存储** | 任务配置保存在 SQLite，重启后自动恢复 |
| **自动重试** | 任务失败时自动重试，确保可靠性 |
| **状态追踪** | 记录每次执行结果，便于审计和调试 |

**三种调度模式对比**：

| 模式 | 说明 | 示例 |
| :--- | :--- | :--- |
| `at` | 指定时间执行一次 | `at: "2024-12-25T09:00:00"` |
| `every` | 周期性执行 | `every: "1h"` (每小时) |
| `cron` | 标准 Cron 表达式 | `cron: "0 9 * * *"` (每天 9 点) |

**常用 Cron 表达式**：

| 表达式 | 说明 |
| :--- | :--- |
| `0 9 * * *` | 每天上午 9:00 |
| `0 */2 * * *` | 每 2 小时 |
| `30 18 * * 1-5` | 工作日下午 6:30 |
| `0 0 1 * *` | 每月 1 日午夜 |
| `0 0 * * 0` | 每周日午夜 |

**使用示例**：

```
用户: 每天早上 9 点提醒我查看邮件

Agent: 好的，我来创建一个定时任务...
       [调用 create_cron 工具]
       ✅ 已创建定时任务
       - 触发时间: 每天 09:00
       - 任务内容: 提醒查看邮件
       - 下次执行: 明天 09:00
```

#### 心跳服务

心跳服务让 Agent 能够定期"醒来"检查是否有待处理任务，实现真正的自主运行。

```mermaid
flowchart LR
    Timer[定时器<br/>默认 30 分钟] --> |唤醒| Check[检查 HEARTBEAT.md]
    Check --> |有任务| LLM[LLM 决策]
    LLM --> |run| Execute[执行任务]
    LLM --> |skip| Wait[继续等待]
```

**核心特性**：

| 特性 | 说明 |
| :--- | :--- |
| **自主唤醒** | 无需用户触发，Agent 定期主动检查 |
| **LLM 决策** | 通过 LLM 智能判断是否需要执行任务 |
| **灵活配置** | 可自定义检查间隔（默认 30 分钟） |
| **会话绑定** | 随 chat 会话启动和停止 |

**工作流程**：

1. Agent 在对话时自动启动心跳服务
2. 每隔指定时间检查 `HEARTBEAT.md` 文件
3. 如果有内容，通过 LLM 决定是否执行
4. LLM 返回 `run` 则执行任务，返回 `skip` 则等待下次检查

**使用示例**：

```
用户: 帮我监控股票价格，跌破 100 元时通知我

Agent: 好的，我会在 HEARTBEAT.md 中记录这个任务...
       心跳服务会定期检查股票价格
       当条件满足时会主动通知你
```

### 3. 记忆自管理：Agentic RAG + 加权 RRF 混合检索

FinchBot 实现了先进的双层记忆架构，让智能体能够自主记忆、检索和遗忘。

#### Agentic RAG 优势

|      对比维度      | 传统 RAG     | Agentic RAG (FinchBot)      |
| :----------------: | :----------- | :-------------------------- |
| **检索触发** | 固定流程     | Agent 自主决策              |
| **检索策略** | 单一向量检索 | 混合检索 + 权重动态调整     |
| **记忆管理** | 被动存储     | 主动 remember/recall/forget |
| **分类能力** | 无           | 自动分类 + 重要性评分       |
| **更新机制** | 全量重建     | 增量同步                    |

#### 记忆工具

智能体可通过三个核心工具自主管理记忆：

| 工具 | 功能 | 使用场景 |
| :--- | :--- | :--- |
| `remember` | 主动存储记忆 | 用户偏好、重要信息、上下文 |
| `recall` | 检索记忆 | 查找历史信息、回忆上下文 |
| `forget` | 删除/归档记忆 | 过期信息、错误记忆、隐私清理 |

**使用示例**：

```
用户: 记住我喜欢用中文交流

Agent: 好的，我会记住这个偏好。
       [调用 remember 工具]
       ✅ 已存储：用户偏好 - 语言：中文

用户: 我之前说过什么语言偏好？

Agent: [调用 recall 工具]
       你之前告诉我喜欢用中文交流。
```

#### 双层存储架构

```mermaid
flowchart TB
    subgraph Business [业务层]
        MM[MemoryManager<br/>remember/recall/forget]
    end

    subgraph Services [服务层]
        RS[RetrievalService<br/>混合检索 + RRF 融合]
        CS[ClassificationService<br/>自动分类]
        IS[ImportanceScorer<br/>重要性评分]
        ES[EmbeddingService<br/>FastEmbed 本地嵌入]
    end

    subgraph Storage [双层存储]
        direction TB
        subgraph Layer1 [第一层：结构化存储]
            SQLite[(SQLiteStore<br/>真相源 · 精确查询)]
        end
        subgraph Layer2 [第二层：向量存储]
            Vector[(VectorStore<br/>ChromaDB · 语义检索)]
        end
        DS[DataSyncManager<br/>增量同步]
    end

    MM --> RS
    MM --> CS
    MM --> IS
    
    RS --> SQLite
    RS --> Vector
    RS --> |RRF 融合| Result[检索结果]
    
    CS --> SQLite
    IS --> SQLite
    ES --> Vector
    
    SQLite <--> DS
    DS <--> Vector
```

#### 混合检索策略

FinchBot 采用**加权 RRF (Weighted Reciprocal Rank Fusion)** 策略：

| 优势 | 说明 |
| :--- | :--- |
| **无需归一化** | 仅基于排名位置计算，无需了解向量或 BM25 分数分布 |
| **抗异常值** | 对单个检索器的异常结果不敏感，更稳定 |
| **共识优先** | 奖励多个检索器都认可的文档，而非单一异常 |
| **权重可控** | 可根据查询类型动态调整关键词/语义检索权重 |

**查询类型自适应权重**：

```python
class QueryType(StrEnum):
    """查询类型，决定检索权重（关键词权重 / 语义权重）"""
    KEYWORD_ONLY = "keyword_only"      # 纯关键词 (1.0/0.0)
    SEMANTIC_ONLY = "semantic_only"    # 纯语义 (0.0/1.0)
    FACTUAL = "factual"                # 事实型 (0.8/0.2)
    CONCEPTUAL = "conceptual"          # 概念型 (0.2/0.8)
    COMPLEX = "complex"                # 复杂型 (0.5/0.5)
    AMBIGUOUS = "ambiguous"            # 歧义型 (0.3/0.7)
```

**RRF 公式**：

```
RRF(d) = Σ (weight_r / (k + rank_r(d)))

其中：
- d 是文档
- k 是平滑常数（通常为 60）
- rank_r(d) 是文档 d 在检索器 r 中的排名
- weight_r 是检索器 r 的权重
```

#### 设计亮点

| 特性 | 说明 |
| :--- | :--- |
| **自主决策** | Agent 根据查询内容选择合适的检索权重 |
| **动态调整** | 事实型查询偏向关键词，概念型查询偏向语义 |
| **迭代验证** | 如果结果不满意，可以调整策略重试 |
| **可解释性** | 每个检索决策都有明确的权重依据 |

### 4. 行为自进化：动态提示词系统

FinchBot 的提示词系统采用文件系统 + 模块化组装的设计，让智能体和用户都能自主修改行为。

#### 动态提示词优势

| 传统方式 | FinchBot 方式 |
| :--- | :--- |
| 提示词硬编码在代码中 | 提示词存储在文件系统中 |
| 修改需要重新部署 | 修改后下次对话自动生效 |
| 用户无法自定义 | 用户可通过编辑文件自定义 |
| Agent 无法调整自身行为 | Agent 可自主优化提示词 |

#### Bootstrap 文件系统

```
~/.finchbot/
├── config.json              # 主配置文件
└── workspace/
    ├── bootstrap/           # Bootstrap 文件目录
    │   ├── SYSTEM.md        # 角色设定（身份、职责、约束）
    │   ├── MEMORY_GUIDE.md  # 记忆使用指南（何时存储/检索）
    │   ├── SOUL.md          # 灵魂设定（性格、语气、风格）
    │   └── AGENT_CONFIG.md  # Agent 配置（模型参数、行为选项）
    ├── config/              # 配置目录
    │   └── mcp.json         # MCP 服务器配置
    ├── generated/           # 自动生成文件
    │   ├── TOOLS.md         # 工具文档（自动生成）
    │   └── CAPABILITIES.md  # 能力信息（自动生成）
    ├── skills/              # 自定义技能
    ├── memory/              # 记忆存储
    └── sessions/            # 会话数据
```

**Bootstrap 文件说明**：

| 文件 | 作用 | 示例内容 |
| :--- | :--- | :--- |
| `SYSTEM.md` | 定义 Agent 的身份和职责 | "你是一个智能助手，擅长..." |
| `MEMORY_GUIDE.md` | 指导 Agent 如何使用记忆 | "用户偏好应存储在长期记忆中..." |
| `SOUL.md` | 定义 Agent 的性格特征 | "你的回复应该简洁、友好..." |
| `AGENT_CONFIG.md` | Agent 行为配置 | 默认语言、响应风格等 |

#### 提示词构建流程

```mermaid
flowchart TD
    A([Agent 启动]) --> B[ContextBuilder<br/>上下文构建器]
    
    B --> C[加载 Bootstrap 文件]
    C --> D[SYSTEM.md]
    C --> E[MEMORY_GUIDE.md]
    C --> F[SOUL.md]
    C --> G[AGENT_CONFIG.md]

    B --> H[加载常驻技能]
    H --> I[SkillsLoader<br/>技能加载器]
    
    B --> J[生成能力信息]
    J --> K[CapabilitiesBuilder<br/>能力构建器]
    K --> L[CAPABILITIES.md]

    D & E & F & G --> M[组装提示词]
    I --> M
    L --> M
    
    M --> N[注入运行时信息<br/>时间/平台/Python版本]
    N --> O[完整系统提示]

    O --> P([发送给 LLM])
```

#### 能力信息自动生成

`CapabilitiesBuilder` 会自动生成能力说明，让 Agent "知道"自己的能力：

```mermaid
flowchart LR
    MCP[MCP 配置] --> Builder[CapabilitiesBuilder]
    Tools[工具列表] --> Builder
    Channels[通道配置] --> Builder

    Builder --> Cap[CAPABILITIES.md<br/>能力说明]
    Builder --> Guide[扩展指南<br/>如何添加 MCP/技能]
```

**生成的 CAPABILITIES.md 包含**：

1. **MCP 服务器状态** — 已配置的服务器列表、启用/禁用状态
2. **MCP 工具列表** — 按服务器分组的可用工具
3. **通道配置** — LangBot 连接状态
4. **扩展指南** — 如何添加新的 MCP 服务器和技能

#### 热加载机制

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 文件系统
    participant C as ContextBuilder
    participant A as Agent

    U->>F: 编辑 SYSTEM.md
    Note over F: 文件修改时间更新
    
    U->>A: 发送新消息
    A->>C: 构建系统提示
    C->>C: 检查文件修改时间
    Note over C: 发现文件已更新
    C->>F: 重新加载 Bootstrap
    C->>A: 返回新提示词
    A-->>U: 使用新行为响应
```

**核心特性**：

| 特性 | 说明 |
| :--- | :--- |
| **用户可定制** | 编辑 Bootstrap 文件即可自定义 Agent 行为 |
| **Agent 可调整** | Agent 可通过 `write_file` 工具修改自身提示词 |
| **立即生效** | 修改后下次对话自动加载，无需重启服务 |
| **智能缓存** | 基于文件修改时间的缓存机制，避免重复构建 |

#### 使用示例

**用户自定义 Agent 性格**：

```bash
# 编辑 SOUL.md 文件
echo "你是一个幽默风趣的助手，喜欢用比喻来解释复杂概念。" > ~/.finchbot/workspace/bootstrap/SOUL.md

# 下次对话立即生效
```

**Agent 自主优化提示词**：

```
用户: 你回复太啰嗦了，简洁一点

Agent: 好的，我会调整我的回复风格。
       [调用 write_file 工具更新 SOUL.md]
       ✅ 已更新我的行为配置，以后会更简洁。
```

### 5. 通道系统：多平台消息支持

FinchBot 集成 LangBot 实现生产级多平台消息支持。

#### LangBot 集成

**为什么选择 LangBot？**
- 15k+ GitHub Stars，活跃维护
- 支持 12+ 平台：QQ、微信、企业微信、飞书、钉钉、Discord、Telegram、Slack、LINE、KOOK、Satori
- 内置 WebUI，可视化配置
- 插件生态，支持 MCP 等扩展

```mermaid
flowchart LR
    FinchBot[FinchBot<br/>Agent 核心] <--> LangBot[LangBot<br/>平台层]

    subgraph Platforms [支持平台]
        direction LR
        QQ[QQ]
        WeChat[微信]
        Feishu[飞书]
        DingTalk[钉钉]
        Discord[Discord]
        Telegram[Telegram]
        Slack[Slack]
    end

    LangBot <--> Platforms
```

#### Webhook 集成流程

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant P as 平台<br/>(QQ/微信等)
    participant L as LangBot
    participant W as Webhook<br/>FastAPI
    participant A as FinchBot<br/>Agent
    participant M as 记忆

    U->>P: 发送消息
    P->>L: 平台适配器
    L->>W: POST /webhook
    W->>W: 解析事件
    W->>A: 创建/获取 Agent
    A->>M: 召回上下文
    M-->>A: 返回记忆
    A->>A: LLM 推理
    A->>M: 存储新记忆
    A-->>W: 响应文本
    W-->>L: WebhookResponse
    L->>P: 发送回复
    P->>U: 显示响应
```

#### 快速开始

```bash
# 终端 1：启动 FinchBot Webhook 服务器
uv run finchbot webhook --port 8000

# 终端 2：启动 LangBot
uvx langbot

# 访问 LangBot WebUI http://localhost:5300
# 配置你的平台并设置 Webhook URL：
# http://localhost:8000/webhook
```

更多详情请参阅 [LangBot 文档](https://docs.langbot.app)。

---

## 链接

- **项目地址**：[GitHub - FinchBot](https://github.com/xt765/FinchBot) | [Gitee - FinchBot](https://gitee.com/xt765/FinchBot)
- **文档**：[FinchBot 文档](https://github.com/xt765/FinchBot/tree/main/docs)
- **问题反馈**：[GitHub Issues](https://github.com/xt765/FinchBot/issues)

---

> 如果对你有帮助，请给个 Star⭐，支持一下！
