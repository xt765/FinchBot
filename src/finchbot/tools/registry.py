"""FinchBot 工具注册表.

参考 Nanobot 的 ToolRegistry 设计，实现动态工具管理和执行。
"""

from typing import Any

from loguru import logger


class ToolRegistry:
    """工具注册表.

    支持动态工具注册、注销和执行，提供统一的工具管理接口。
    """

    def __init__(self) -> None:
        """初始化工具注册表."""
        self._tools: dict[str, Any] = {}

    def register(self, tool: Any) -> None:
        """注册工具.

        Args:
            tool: 工具实例，必须包含 name 属性。
        """
        if not hasattr(tool, "name"):
            raise ValueError("Tool must have a 'name' attribute")

        tool_name = tool.name
        if tool_name in self._tools:
            logger.warning(f"Tool '{tool_name}' already registered, overwriting")

        self._tools[tool_name] = tool
        logger.debug(f"Tool '{tool_name}' registered")

    def unregister(self, name: str) -> None:
        """注销工具.

        Args:
            name: 工具名称。
        """
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"Tool '{name}' unregistered")
        else:
            logger.warning(f"Tool '{name}' not found, cannot unregister")

    def get(self, name: str) -> Any | None:
        """获取工具实例.

        Args:
            name: 工具名称。

        Returns:
            工具实例，未找到则返回 None。
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """检查工具是否已注册.

        Args:
            name: 工具名称。

        Returns:
            是否已注册。
        """
        return name in self._tools

    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具定义（OpenAI 格式）.

        Returns:
            工具定义列表。
        """
        definitions = []
        for tool in self._tools.values():
            if hasattr(tool, "to_schema"):
                definitions.append(tool.to_schema())
            elif hasattr(tool, "parameters"):
                definitions.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": getattr(tool, "description", ""),
                            "parameters": getattr(tool, "parameters", {}),
                        },
                    }
                )
        return definitions

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """执行工具.

        Args:
            name: 工具名称。
            params: 工具参数。

        Returns:
            工具执行结果字符串。
        """
        tool = self._tools.get(name)
        if not tool:
            error_msg = f"工具 '{name}' 未找到"
            logger.error(error_msg)
            return f"错误: {error_msg}"

        try:
            logger.debug(f"执行工具 '{name}'，参数: {params}")

            # 检查工具是否有 validate_params 方法
            if hasattr(tool, "validate_params"):
                errors = tool.validate_params(params)
                if errors:
                    error_msg = f"工具 '{name}' 参数验证失败: {errors}"
                    logger.error(error_msg)
                    return f"错误: {error_msg}"

            # 执行工具
            result = None
            if hasattr(tool, "execute"):
                result = await tool.execute(**params)
            elif hasattr(tool, "_run"):
                result = await tool._run(**params)
            elif hasattr(tool, "run"):
                result = await tool.run(**params)
            elif callable(tool):
                # 对于可调用对象，需要检查是否是协程函数
                import asyncio

                if asyncio.iscoroutinefunction(tool):
                    result = await tool(**params)
                else:
                    result = tool(**params)
            else:
                error_msg = f"工具 '{name}' 没有可执行的方法"
                logger.error(error_msg)
                return f"错误: {error_msg}"

            logger.debug(f"工具 '{name}' 执行成功")
            return str(result)

        except Exception as e:
            error_msg = f"执行工具 '{name}' 时出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"错误: {error_msg}"

    @property
    def tool_names(self) -> list[str]:
        """获取所有已注册工具名称.

        Returns:
            工具名称列表。
        """
        return list(self._tools.keys())

    def __len__(self) -> int:
        """获取已注册工具数量."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """检查工具是否已注册."""
        return name in self._tools

    def __str__(self) -> str:
        """字符串表示."""
        return f"ToolRegistry({len(self)} tools: {', '.join(self.tool_names)})"


# 全局工具注册表实例
_global_registry: ToolRegistry | None = None


def get_global_registry() -> ToolRegistry:
    """获取全局工具注册表实例.

    Returns:
        全局工具注册表实例。
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool: Any) -> None:
    """注册工具到全局注册表.

    Args:
        tool: 工具实例。
    """
    registry = get_global_registry()
    registry.register(tool)


def unregister_tool(name: str) -> None:
    """从全局注册表注销工具.

    Args:
        name: 工具名称。
    """
    registry = get_global_registry()
    registry.unregister(name)


async def execute_tool(name: str, params: dict[str, Any]) -> str:
    """通过全局注册表执行工具.

    Args:
        name: 工具名称。
        params: 工具参数。

    Returns:
        工具执行结果。
    """
    registry = get_global_registry()
    return await registry.execute(name, params)
