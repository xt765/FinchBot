"""FinchBot 工具基类.

基于 LangChain BaseTool 实现，提供统一的工具接口。
"""

from abc import abstractmethod
from typing import Any

from langchain_core.tools import BaseTool


class FinchTool(BaseTool):
    """FinchBot 工具基类.

    继承 LangChain BaseTool，提供统一的工具接口。
    所有 FinchBot 工具都应继承此类。

    Attributes:
        name: 工具名称，用于函数调用。
        description: 工具描述，说明工具功能。
    """

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """返回工具参数的 JSON Schema.

        Returns:
            参数定义字典，符合 JSON Schema 规范。
        """
        pass

    def to_openai_schema(self) -> dict[str, Any]:
        """转换为 OpenAI 函数调用格式.

        Returns:
            OpenAI 格式的工具定义字典。
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
