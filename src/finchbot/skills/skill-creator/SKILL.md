---
name: skill-creator
description: 创建或更新 Agent 技能。用于设计、构建或打包技能，包括脚本、参考资料和资源文件。
metadata: {"finchbot":{"emoji":"🛠️","always":false}}
---

# 技能创建指南

本技能提供创建有效 Agent 技能的指导。

## 关于技能

技能是模块化、自包含的包，通过提供专业知识、工作流程和工具来扩展 Agent 的能力。可以把它们看作特定领域或任务的"入门指南"。

### 技能提供的功能

1. **专业工作流程** - 特定领域的多步骤流程
2. **工具集成** - 处理特定文件格式或 API 的说明
3. **领域专业知识** - 公司特定知识、模式、业务逻辑
4. **打包资源** - 用于复杂和重复任务的脚本、参考资料和资源文件

## 核心原则

### 简洁是关键

上下文窗口是公共资源。技能与 Agent 需要的所有其他内容共享上下文窗口。

**默认假设：Agent 已经非常聪明。** 只添加 Agent 尚未拥有的上下文。

优先使用简洁的示例而不是冗长的解释。

### 技能的结构

每个技能由必需的 SKILL.md 文件和可选的打包资源组成：

```
skill-name/
├── SKILL.md (必需)
│   ├── YAML frontmatter 元数据 (必需)
│   │   ├── name: (必需)
│   │   └── description: (必需)
│   └── Markdown 使用说明 (必需)
└── 打包资源 (可选)
    ├── scripts/          - 可执行代码 (Python/Bash 等)
    ├── references/       - 文档，按需加载到上下文
    └── assets/           - 输出中使用的文件 (模板、图标、字体等)
```

#### SKILL.md (必需)

每个 SKILL.md 包含：

- **Frontmatter** (YAML)：包含 `name` 和 `description` 字段
- **正文** (Markdown)：使用技能的说明和指南

#### 技能 Frontmatter 示例

```yaml
---
name: weather
description: 查询当前天气和天气预报（无需 API 密钥）。
homepage: https://wttr.in/:help
metadata: {"finchbot":{"emoji":"🌤️","requires":{"bins":["curl"]}}}
---
```

### 如何创建技能

1. **创建技能目录**：`skills/{skill-name}/`
2. **创建 SKILL.md**：添加 frontmatter 和说明
3. **添加可选资源**：根据需要添加 scripts/、references/、assets/
4. **测试技能**：验证它能正常工作

### 技能命名

- 仅使用小写字母、数字和连字符
- 优先使用简短的、以动词开头的短语来描述动作
- 技能文件夹名称与技能名称完全一致

### 快速入门模板

这是一个最小化的 SKILL.md 模板：

```yaml
---
name: my-skill
description: 简短描述这个技能的功能和使用时机。
metadata: {"finchbot":{"emoji":"✨"}}
---

# 我的技能

关于如何使用这个技能的简要说明。
```
