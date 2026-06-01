"""工具注册表核心.

统一管理所有工具的注册、实例化和执行。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool
from loguru import logger

from finchbot.tools.decorator import ToolMeta

if TYPE_CHECKING:
    from finchbot.config.schema import Config


@dataclass
class ToolEntry:
    """工具条目."""

    tool: BaseTool
    meta: ToolMeta
    instance: Any = None
    enabled: bool = True
    source: str = "builtin"


class ToolRegistry:
    """工具注册表.

    统一管理所有工具的注册、实例化和执行。

    Attributes:
        _tools: 工具条目映射
        _by_category: 分类索引
        _workspace: 工作区路径
        _config: 配置对象
    """

    _instance: ToolRegistry | None = None

    def __init__(self, workspace: Path, config: Config) -> None:
        self._tools: dict[str, ToolEntry] = {}
        self._by_category: dict[str, list[str]] = {}
        self._workspace = workspace
        self._config = config
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> ToolRegistry | None:
        """获取单例实例."""
        return cls._instance

    @classmethod
    def set_instance(cls, instance: ToolRegistry) -> None:
        """设置单例实例."""
        cls._instance = instance

    async def initialize(self) -> list[BaseTool]:
        """初始化注册表.

        加载所有已注册的工具，创建实例。

        Returns:
            工具列表
        """
        from finchbot.tools.discovery import ToolDiscovery
        registry = ToolDiscovery().discover_all()

        for name, (tool_or_class, meta) in registry.items():
            try:
                tool = await self._create_tool_instance(tool_or_class, meta)
                if tool:
                    self._register(name, tool, meta)
            except Exception as e:
                logger.error(f"初始化工具 '{name}' 失败: {e}")

        logger.info(f"工具注册表初始化完成: {len(self._tools)} 个工具")
        return self.get_tools()

    async def _create_tool_instance(
        self,
        tool_or_class: Any,
        meta: ToolMeta,
    ) -> BaseTool | None:
        """创建工具实例.

        Args:
            tool_or_class: 工具函数或类
            meta: 工具元数据

        Returns:
            工具实例，失败返回 None
        """
        if isinstance(tool_or_class, BaseTool):
            return tool_or_class

        if isinstance(tool_or_class, type):
            kwargs = {}

            if meta.requires_workspace:
                kwargs["workspace"] = self._workspace
            if meta.requires_config:
                kwargs["config"] = self._config

            try:
                instance = tool_or_class(**kwargs)
                if callable(instance):
                    from langchain_core.tools import tool as lc_tool

                    @lc_tool(name=meta.name, description=meta.description)
                    async def wrapper(**args):
                        if asyncio.iscoroutinefunction(instance):
                            return await instance(**args)
                        return instance(**args)

                    return wrapper
                return instance
            except Exception as e:
                logger.warning(f"创建工具实例失败: {e}")
                return None

        return tool_or_class

    def _register(self, name: str, tool: BaseTool, meta: ToolMeta) -> None:
        """注册工具.

        Args:
            name: 工具名称
            tool: 工具实例
            meta: 工具元数据
        """
        entry = ToolEntry(
            tool=tool,
            meta=meta,
            enabled=meta.enabled_by_default,
            source="builtin",
        )
        self._tools[name] = entry

        category = meta.category.value
        if category not in self._by_category:
            self._by_category[category] = []
        self._by_category[category].append(name)

    def register(self, tool: BaseTool, meta: ToolMeta, source: str = "dynamic") -> None:
        """动态注册工具.

        Args:
            tool: 工具实例
            meta: 工具元数据
            source: 工具来源
        """
        entry = ToolEntry(
            tool=tool,
            meta=meta,
            enabled=True,
            source=source,
        )
        self._tools[tool.name] = entry

        category = meta.category.value
        if category not in self._by_category:
            self._by_category[category] = []
        self._by_category[category].append(tool.name)

        logger.info(f"动态注册工具: {tool.name} (来源: {source})")

    def unregister(self, name: str) -> bool:
        """注销工具.

        Args:
            name: 工具名称

        Returns:
            是否成功注销
        """
        if name in self._tools:
            entry = self._tools.pop(name)
            category = entry.meta.category.value
            if category in self._by_category:
                self._by_category[category] = [n for n in self._by_category[category] if n != name]
            logger.info(f"注销工具: {name}")
            return True
        return False

    def get_tool(self, name: str) -> BaseTool | None:
        """获取工具.

        Args:
            name: 工具名称

        Returns:
            工具实例，不存在或已禁用返回 None
        """
        entry = self._tools.get(name)
        return entry.tool if entry and entry.enabled else None

    def get_tools(self, enabled_only: bool = True) -> list[BaseTool]:
        """获取所有工具.

        Args:
            enabled_only: 是否只返回启用的工具

        Returns:
            工具列表
        """
        return [entry.tool for entry in self._tools.values() if not enabled_only or entry.enabled]

    def get_tools_by_category(self, category: str) -> list[BaseTool]:
        """按分类获取工具.

        Args:
            category: 分类名称

        Returns:
            工具列表
        """
        names = self._by_category.get(category, [])
        return [self._tools[n].tool for n in names if n in self._tools and self._tools[n].enabled]

    def get_tools_by_source(self, source: str) -> list[BaseTool]:
        """按来源获取工具.

        Args:
            source: 来源名称

        Returns:
            工具列表
        """
        return [
            entry.tool for entry in self._tools.values() if entry.source == source and entry.enabled
        ]

    def enable(self, name: str) -> bool:
        """启用工具.

        Args:
            name: 工具名称

        Returns:
            是否成功启用
        """
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """禁用工具.

        Args:
            name: 工具名称

        Returns:
            是否成功禁用
        """
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    async def execute(self, name: str, arguments: dict) -> str:
        """执行工具.

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            执行结果
        """
        tool = self.get_tool(name)
        if not tool:
            return f"错误: 工具 '{name}' 未找到或已禁用"

        try:
            result = await tool.ainvoke(arguments)
            return str(result)
        except Exception as e:
            logger.error(f"执行工具 '{name}' 失败: {e}")
            return f"错误: {e}"

    def get_status(self) -> dict[str, dict]:
        """获取所有工具状态.

        Returns:
            工具状态映射
        """
        return {
            name: {
                "enabled": entry.enabled,
                "category": entry.meta.category.value,
                "source": entry.source,
                "description": entry.meta.description,
            }
            for name, entry in self._tools.items()
        }

    def get_tool_names(self) -> list[str]:
        """获取所有工具名称.

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """检查工具是否存在.

        Args:
            name: 工具名称

        Returns:
            是否存在
        """
        return name in self._tools

    def count(self, enabled_only: bool = False) -> int:
        """统计工具数量.

        Args:
            enabled_only: 是否只统计启用的工具

        Returns:
            工具数量
        """
        if enabled_only:
            return sum(1 for e in self._tools.values() if e.enabled)
        return len(self._tools)

    @property
    def tool_names(self) -> list[str]:
        """获取所有已注册工具名称（兼容属性）.

        Returns:
            工具名称列表。
        """
        return self.get_tool_names()

    def get(self, name: str) -> BaseTool | None:
        """获取工具实例（兼容方法）.

        Args:
            name: 工具名称。

        Returns:
            工具实例，未找到则返回 None。
        """
        return self.get_tool(name)

    def has(self, name: str) -> bool:
        """检查工具是否已注册（兼容方法）.

        Args:
            name: 工具名称。

        Returns:
            是否已注册。
        """
        return self.has_tool(name)

    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具定义（OpenAI 格式）.

        Returns:
            工具定义列表。
        """
        definitions = []
        for entry in self._tools.values():
            tool = entry.tool
            if hasattr(tool, "to_schema"):
                definitions.append(tool.to_schema())
            elif hasattr(tool, "args_schema"):
                try:
                    schema = tool.args_schema.schema()
                    definitions.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": getattr(tool, "description", ""),
                                "parameters": schema,
                            },
                        }
                    )
                except Exception:
                    pass
        return definitions

    def __len__(self) -> int:
        """获取已注册工具数量."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """检查工具是否已注册."""
        return name in self._tools

    def __str__(self) -> str:
        """字符串表示."""
        return f"ToolRegistry({len(self)} tools: {', '.join(self.tool_names)})"


def get_global_registry() -> ToolRegistry:
    """获取全局工具注册表实例.

    如果未设置单例，创建一个默认实例。

    Returns:
        全局工具注册表实例。
    """
    instance = ToolRegistry.get_instance()
    if instance is None:
        from pathlib import Path

        from finchbot.config import load_config

        workspace = Path.cwd()
        config = load_config()
        instance = ToolRegistry(workspace, config)
        ToolRegistry.set_instance(instance)
    return instance


def register_tool(tool: BaseTool, meta: ToolMeta | None = None, source: str = "dynamic") -> None:
    """注册工具到全局注册表.

    Args:
        tool: 工具实例。
        meta: 工具元数据（可选）。
        source: 工具来源。
    """
    registry = get_global_registry()
    if meta is None:
        from finchbot.tools.decorator import ToolCategory, ToolMeta

        meta = ToolMeta(
            name=tool.name,
            description=getattr(tool, "description", ""),
            category=ToolCategory.PLUGIN,
        )
    registry.register(tool, meta, source)


def unregister_tool(name: str) -> bool:
    """从全局注册表注销工具.

    Args:
        name: 工具名称。

    Returns:
        是否成功注销
    """
    registry = get_global_registry()
    return registry.unregister(name)


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
