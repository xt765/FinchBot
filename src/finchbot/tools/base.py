"""FinchBot 工具基类.

基于 LangChain BaseTool 实现，提供统一的工具接口。
参考 Nanobot 的 Tool 设计，增强验证和错误处理。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from loguru import logger
from pydantic import Field


class FinchTool(BaseTool):
    """FinchBot 工具基类.

    继承 LangChain BaseTool，提供统一的工具接口。
    所有 FinchBot 工具都应继承此类。

    Attributes:
        name: 工具名称，用于函数调用。
        description: 工具描述，说明工具功能。
        parameters: 工具参数定义（可选）。
        allowed_dirs: 允许访问的目录列表（可选）。
        workspace: 工作目录路径（可选）。
    """

    name: str = Field(default="", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)

    allowed_dirs: list[Path] | None = None

    @property
    def parameters(self) -> dict[str, Any]:
        """返回工具参数定义.

        子类可以覆写此属性以提供自定义参数定义。
        """
        return {}

    def validate_path(self, path: str) -> Path | None:
        """验证并解析路径.

        检查路径是否在允许的目录范围内，防止越权访问。

        Args:
            path: 要验证的路径字符串。

        Returns:
            解析后的绝对路径，如果验证失败返回 None。
        """
        try:
            resolved = Path(path).expanduser().resolve()

            # 如果没有设置允许目录，允许所有路径
            if self.allowed_dirs is None:
                return resolved

            # 检查路径是否在允许的目录内
            allowed_dirs = self.allowed_dirs
            if isinstance(allowed_dirs, Path):
                allowed_dirs = [allowed_dirs]

            in_allowed = any(str(resolved).startswith(str(d.resolve())) for d in allowed_dirs)
            if not in_allowed:
                logger.warning(f"Path {path} not in allowed directories")
                return None

            return resolved
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return None

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
        return (
            f"FinchTool(name='{self.name}', description='{self.description}', parameters={params})"
        )
