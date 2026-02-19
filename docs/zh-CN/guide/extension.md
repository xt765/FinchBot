# 扩展指南

FinchBot 提供了强大的扩展能力，允许开发者通过 **添加新工具 (Tools)** 和 **编写新技能 (Skills)** 来增强 Agent 的能力。

## 1. 添加新工具 (Add New Tools)

工具是 Python 代码，用于执行实际操作（如调用 API、处理数据、操作文件等）。所有工具必须继承自 `finchbot.tools.base.FinchTool`。

### 步骤 1: 创建工具类

创建一个新的 Python 文件（例如 `src/finchbot/tools/custom/my_tool.py`），并定义工具类。

```python
from typing import Any
from pydantic import Field
from finchbot.tools.base import FinchTool

class WeatherTool(FinchTool):
    """天气查询工具.
    
    允许 Agent 查询指定城市的天气情况。
    """
    
    # 工具名称，Agent 调用时使用
    name: str = "get_weather"
    
    # 工具描述，帮助 Agent 理解何时使用该工具
    description: str = "Get current weather for a specific city."
    
    # 参数定义 (JSON Schema)
    parameters: dict = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "The name of the city, e.g. Beijing, New York",
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Temperature unit",
                "default": "celsius"
            }
        },
        "required": ["city"],
    }

    def _run(self, city: str, unit: str = "celsius") -> str:
        """同步执行逻辑."""
        # 这里实现实际的 API 调用逻辑
        # 示例返回值
        return f"The weather in {city} is Sunny, 25 degrees {unit}."

    async def _arun(self, city: str, unit: str = "celsius") -> str:
        """异步执行逻辑 (可选)."""
        # 如果需要异步操作，请实现此方法
        return self._run(city, unit)
```

### 步骤 2: 注册工具

在 `src/finchbot/agent/core.py` 的 `_register_default_tools` 函数中注册您的新工具，或者在创建 Agent 时动态传入。

**方法 A: 修改源码注册 (推荐用于内置工具)**

修改 `src/finchbot/agent/core.py`:

```python
from finchbot.tools.custom.my_tool import WeatherTool

def _register_default_tools():
    # ...
    tools = [
        # ... 现有工具
        WeatherTool(),  # 添加新工具
    ]
    # ...
```

**方法 B: 运行时注册 (推荐用于插件)**

```python
from finchbot.tools.registry import register_tool
from my_plugin import WeatherTool

register_tool(WeatherTool())
```

---

## 2. 编写新技能 (Add New Skills)

技能 (Skills) 是基于 Markdown 的文档，用于教导 Agent 如何处理特定类型的任务。它们类似于 "标准作业程序 (SOP)" 或 "In-Context Learning" 示例。

### 技能目录结构

技能文件存放在工作区的 `skills/` 目录下（默认为 `~/.finchbot/workspace/skills/`）。

```text
workspace/
  skills/
    data-analysis/
      SKILL.md      # 技能定义文件
    python-coding/
      SKILL.md
```

### 步骤 1: 创建技能目录

在 `skills/` 下创建一个新目录，例如 `report-writing`。

### 步骤 2: 编写 SKILL.md

在目录中创建 `SKILL.md` 文件。文件包含 **YAML Frontmatter** 和 **Markdown 正文**。

**示例**:

```markdown
---
name: report-writing
description: 指导 Agent 如何撰写专业的分析报告。
metadata:
  finchbot:
    emoji: 📝
    always: false  # 是否总是加载此技能 (true/false)
---

# 报告撰写指南

当用户要求撰写分析报告时，请遵循以下结构和原则：

## 1. 结构要求

*   **标题**: 清晰反映主题。
*   **摘要 (Executive Summary)**: 简要概述核心发现（200字以内）。
*   **方法论**: 说明数据来源和分析方法。
*   **详细分析**: 分点阐述，使用数据支撑观点。
*   **结论与建议**: 给出可执行的建议。

## 2. 写作风格

*   保持客观、中立。
*   使用专业术语，但对生僻词进行解释。
*   多使用列表和表格来展示数据。

## 3. 示例

**用户**: 请分析一下 Q1 的销售数据。

**Agent**:
# 2024年第一季度销售数据分析报告

## 摘要
本季度销售额同比增长 15%，主要由...
...
```

### 技能加载机制

1.  **自动发现**: Agent 启动时会自动扫描 `skills/` 目录。
2.  **动态注入**: 
    *   如果 `always: true`，技能内容会被直接拼接到 System Prompt 中。
    *   如果 `always: false`，技能的 `name` 和 `description` 会出现在 System Prompt 的可用技能列表中。Agent 可以根据当前任务决定是否通过“回忆”或“阅读”来获取技能的详细内容。

---

## 3. 最佳实践

*   **工具 vs 技能**: 
    *   如果任务需要**执行动作**（如联网、读文件、计算），使用 **工具**。
    *   如果任务需要**遵循流程**或**特定风格**（如写代码规范、回答风格），使用 **技能**。
*   **原子性**: 保持工具功能单一，一个工具只做一件事。
*   **文档**: 为工具编写清晰的 `description` 和 `parameters` 说明，这直接决定了 LLM 能否正确调用它。
