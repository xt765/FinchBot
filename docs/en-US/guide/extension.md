# Extension Guide

FinchBot provides powerful extensibility, allowing developers to enhance the Agent's capabilities by **Adding New Tools** and **Writing New Skills**.

## 1. Adding New Tools

Tools are Python code used to perform actual operations (e.g., calling APIs, processing data, manipulating files). All tools must inherit from `finchbot.tools.base.FinchTool`.

### Step 1: Create a Tool Class

Create a new Python file (e.g., `src/finchbot/tools/custom/my_tool.py`) and define the tool class.

```python
from typing import Any
from pydantic import Field
from finchbot.tools.base import FinchTool

class WeatherTool(FinchTool):
    """Weather Query Tool.
    
    Allows the Agent to query weather conditions for a specific city.
    """
    
    # Tool name, used by the Agent when calling
    name: str = "get_weather"
    
    # Tool description, helps the Agent understand when to use this tool
    description: str = "Get current weather for a specific city."
    
    # Parameter definition (JSON Schema)
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
        """Synchronous execution logic."""
        # Implement actual API call logic here
        return f"The weather in {city} is Sunny, 25 degrees {unit}."

    async def _arun(self, city: str, unit: str = "celsius") -> str:
        """Asynchronous execution logic (optional)."""
        return self._run(city, unit)
```

### Step 2: Register the Tool

Register your new tool in `src/finchbot/agent/core.py`'s `_register_default_tools` function, or pass it dynamically when creating the Agent.

**Method A: Source Code Registration (Recommended for built-in tools)**

Modify `src/finchbot/agent/core.py`:

```python
from finchbot.tools.custom.my_tool import WeatherTool

def _register_default_tools():
    # ...
    tools = [
        # ... existing tools
        WeatherTool(),  # Add new tool
    ]
    # ...
```

**Method B: Runtime Registration (Recommended for plugins)**

```python
from finchbot.tools.registry import register_tool
from my_plugin import WeatherTool

register_tool(WeatherTool())
```

---

## 2. Writing New Skills

Skills are Markdown-based documents used to teach the Agent how to handle specific types of tasks. They are similar to "Standard Operating Procedures (SOPs)" or "In-Context Learning" examples.

### Skill Directory Structure

Skill files are stored in the `skills/` directory of the workspace (default: `~/.finchbot/workspace/skills/`).

```text
workspace/
  skills/
    data-analysis/
      SKILL.md      # Skill definition file
    python-coding/
      SKILL.md
```

### Step 1: Create Skill Directory

Create a new directory under `skills/`, e.g., `report-writing`.

### Step 2: Write SKILL.md

Create a `SKILL.md` file in the directory. The file contains **YAML Frontmatter** and **Markdown Body**.

**Example**:

```markdown
---
name: report-writing
description: Guide the Agent on how to write professional analysis reports.
metadata:
  finchbot:
    emoji: 📝
    always: false  # Whether to always load this skill (true/false)
---

# Report Writing Guide

When the user requests an analysis report, please follow these structures and principles:

## 1. Structure Requirements

*   **Title**: Clearly reflects the topic.
*   **Executive Summary**: Briefly outline core findings (within 200 words).
*   **Methodology**: Explain data sources and analysis methods.
*   **Detailed Analysis**: Elaborate point by point, using data to support arguments.
*   **Conclusion & Recommendations**: Provide actionable suggestions.

## 2. Writing Style

*   Maintain objectivity and neutrality.
*   Use professional terminology but explain obscure words.
*   Use lists and tables frequently to display data.

## 3. Example

**User**: Please analyze the Q1 sales data.

**Agent**:
# Q1 2024 Sales Data Analysis Report

## Summary
Sales this quarter increased by 15% year-over-year, mainly driven by...
...
```

### Skill Loading Mechanism

1.  **Auto-discovery**: The Agent automatically scans the `skills/` directory on startup.
2.  **Dynamic Injection**: 
    *   If `always: true`, skill content is directly appended to the System Prompt.
    *   If `always: false`, the skill's `name` and `description` appear in the System Prompt's available skills list. The Agent can decide whether to fetch the skill's detailed content via "recall" or "read" based on the current task.
