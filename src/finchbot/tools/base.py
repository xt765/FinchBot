"""FinchBot 工具基类.

基于 LangChain BaseTool 实现，提供统一的工具接口。
参考 Nanobot 的 Tool 设计，增强验证和错误处理。
"""

from abc import abstractmethod
from typing import Any

from langchain_core.tools import BaseTool
from loguru import logger


class FinchTool(BaseTool):
    """FinchBot 工具基类.

    继承 LangChain BaseTool，提供统一的工具接口。
    所有 FinchBot 工具都应继承此类。

    Attributes:
        name: 工具名称，用于函数调用。
        description: 工具描述，说明工具功能。
    """

    # 注意：移除 parameters 属性定义，因为 LangChain 的 BaseTool 已经有自己的参数管理机制
    # 我们将通过 Pydantic 字段或 args_schema 来管理参数，或者让子类自己实现 schema 生成
    
    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """验证工具参数.

        Args:
            params: 工具参数字典。

        Returns:
            错误消息列表，空列表表示验证通过。
        """
        errors = []
        
        # 获取子类定义的 parameters 字典（如果有）
        if hasattr(self, "parameters") and isinstance(self.parameters, dict):
            parameters = self.parameters
            
            # 检查必需参数
            required_params = parameters.get("required", [])
            for param_name in required_params:
                if param_name not in params:
                    errors.append(f"必需参数 '{param_name}' 缺失")

            # 检查参数类型（简化验证）
            param_props = parameters.get("properties", {})
            for param_name, param_value in params.items():
                if param_name in param_props:
                    param_schema = param_props[param_name]
                    param_type = param_schema.get("type")

                    if param_type == "string" and not isinstance(param_value, str):
                        errors.append(f"参数 '{param_name}' 应为字符串类型")
                    elif param_type == "integer" and not isinstance(param_value, int):
                        errors.append(f"参数 '{param_name}' 应为整数类型")
                    elif param_type == "boolean" and not isinstance(param_value, bool):
                        errors.append(f"参数 '{param_name}' 应为布尔类型")

        if errors:
            logger.warning(f"工具 '{self.name}' 参数验证失败: {errors}")

        return errors

    def to_schema(self) -> dict[str, Any]:
        """转换为工具定义格式（兼容 OpenAI 和 LangChain）.

        Returns:
            工具定义字典。
        """
        # 尝试获取 parameters 属性，如果不存在则设为空字典
        params = getattr(self, "parameters", {})
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }

    def to_openai_schema(self) -> dict[str, Any]:
        """转换为 OpenAI 函数调用格式（兼容性方法）.

        Returns:
            OpenAI 格式的工具定义字典。
        """
        return self.to_schema()

    def __str__(self) -> str:
        """字符串表示."""
        return f"FinchTool(name='{self.name}', description='{self.description}')"

    def __repr__(self) -> str:
        """详细表示."""
        params = getattr(self, "parameters", {})
        return f"FinchTool(name='{self.name}', description='{self.description}', parameters={params})"
