"""MCP 热更新管理器.

管理 MCP 配置变更的检测、处理和文档更新。
支持在对话过程中热更新 MCP 工具。
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool
from loguru import logger

from finchbot.tools.core import ToolRegistry
from finchbot.tools.decorator import ToolCategory, ToolMeta

if TYPE_CHECKING:
    from finchbot.config.schema import Config


class MCPHotUpdateManager:
    """MCP 热更新管理器.

    管理 MCP 配置变更的完整处理流程：
    1. 检测配置变更
    2. 重新连接 MCP 服务器
    3. 更新工具注册表
    4. 更新相关文档
    5. 通知 Agent

    Attributes:
        workspace: 工作区路径
        config: 配置对象
        registry: 工具注册表
        _mcp_connector: MCP 连接器
        _config_hash: 配置文件哈希
        _on_update_callbacks: 更新完成回调列表
    """

    _instance: MCPHotUpdateManager | None = None

    def __init__(
        self,
        workspace: Path,
        config: Config,
        registry: ToolRegistry,
    ) -> None:
        self.workspace = workspace
        self.config = config
        self.registry = registry
        self._mcp_connector: Any = None
        self._config_hash: str = ""
        self._on_update_callbacks: list[Callable[[], None]] = []
        self._lock = asyncio.Lock()
        self._pending_update = False
        self._last_update_time: float = 0

    @classmethod
    def get_instance(cls) -> MCPHotUpdateManager | None:
        """获取单例实例."""
        return cls._instance

    @classmethod
    def set_instance(cls, instance: MCPHotUpdateManager) -> None:
        """设置单例实例."""
        cls._instance = instance

    def on_update(self, callback: Callable[[], None]) -> None:
        """注册更新完成回调.

        Args:
            callback: 回调函数
        """
        self._on_update_callbacks.append(callback)

    async def initialize(self) -> list[BaseTool]:
        """初始化 MCP 工具.

        Returns:
            MCP 工具列表
        """
        tools = await self._connect_mcp_servers()
        self._config_hash = self._compute_config_hash()
        self._register_tools(tools)

        await self._update_documents()

        logger.info(f"MCP 初始化完成: {len(tools)} 个工具")
        return tools

    async def on_config_changed(self) -> None:
        """配置变更回调.

        由文件监控器或 configure_mcp 工具调用。
        标记需要更新，在下次模型调用时执行。
        """
        logger.info("检测到 MCP 配置变更")
        self._pending_update = True

    async def check_and_update(self) -> list[BaseTool] | None:
        """检查并执行更新.

        由 Middleware 在模型调用前调用。
        如果有待处理的更新，执行热更新。

        Returns:
            更新后的工具列表，如果无更新返回 None
        """
        if not self._pending_update:
            return None

        return await self.hot_reload()

    async def hot_reload(self) -> list[BaseTool]:
        """执行热更新.

        完整的热更新流程：
        1. 断开旧连接
        2. 加载新配置
        3. 连接新服务器
        4. 更新注册表
        5. 更新文档
        6. 通知回调

        Returns:
            更新后的 MCP 工具列表
        """
        async with self._lock:
            logger.info("开始 MCP 热更新...")

            old_tools = self.registry.get_tools_by_source("mcp")
            for tool in old_tools:
                self.registry.unregister(tool.name)
            logger.debug(f"移除 {len(old_tools)} 个旧 MCP 工具")

            if self._mcp_connector:
                try:
                    await self._mcp_connector.stop()
                except Exception as e:
                    logger.warning(f"断开 MCP 连接时出错: {e}")
                self._mcp_connector = None

            new_tools = await self._connect_mcp_servers()

            self._register_tools(new_tools)

            self._config_hash = self._compute_config_hash()
            self._pending_update = False
            self._last_update_time = asyncio.get_event_loop().time()

            await self._update_documents()

            for callback in self._on_update_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.warning(f"更新回调执行失败: {e}")

            logger.info(f"MCP 热更新完成: {len(new_tools)} 个工具")
            return new_tools

    async def _connect_mcp_servers(self) -> list[BaseTool]:
        """连接 MCP 服务器.

        Returns:
            MCP 工具列表
        """
        from finchbot.config.loader import load_mcp_config

        try:
            from finchbot.tools.mcp.connector import MCPConnector
        except ImportError:
            logger.warning("MCP 连接器模块未找到")
            return []

        mcp_servers = load_mcp_config(self.workspace)
        if not mcp_servers:
            logger.info("无 MCP 配置")
            return []

        self.config.mcp.servers = mcp_servers

        try:
            self._mcp_connector = MCPConnector(self.config)
            await self._mcp_connector.start()
            tools = await self._mcp_connector.connect_all()
            return tools

        except ImportError as e:
            logger.warning(f"MCP 依赖未安装: {e}")
            return []
        except Exception as e:
            logger.error(f"连接 MCP 服务器失败: {e}", exc_info=True)
            return []

    def _register_tools(self, tools: list[BaseTool]) -> None:
        """注册 MCP 工具到注册表.

        Args:
            tools: 工具列表
        """
        for tool in tools:
            meta = ToolMeta(
                name=tool.name,
                description=tool.description,
                category=ToolCategory.MCP,
            )
            self.registry.register(tool, meta, source="mcp")

    async def _update_documents(self) -> None:
        """更新 MCP 相关文档."""
        await asyncio.gather(
            self._update_capabilities_md(),
            self._update_tools_md(),
            self._update_mcp_status_md(),
        )

    async def _update_capabilities_md(self) -> None:
        """更新 CAPABILITIES.md."""
        try:
            from finchbot.agent.capabilities import write_capabilities_md

            tools = self.registry.get_tools()
            write_capabilities_md(self.workspace, self.config, tools)
            logger.debug("CAPABILITIES.md 已更新")
        except Exception as e:
            logger.warning(f"更新 CAPABILITIES.md 失败: {e}")

    async def _update_tools_md(self) -> None:
        """更新 TOOLS.md."""
        try:
            tools = self.registry.get_tools()
            tools_content = self._generate_tools_md(tools)

            tools_path = self.workspace / "generated" / "TOOLS.md"
            tools_path.parent.mkdir(parents=True, exist_ok=True)
            tools_path.write_text(tools_content, encoding="utf-8")

            logger.debug("TOOLS.md 已更新")
        except Exception as e:
            logger.warning(f"更新 TOOLS.md 失败: {e}")

    async def _update_mcp_status_md(self) -> None:
        """更新 MCP_STATUS.md."""
        try:
            status = self.get_mcp_status()
            content = self._generate_mcp_status_md(status)

            status_path = self.workspace / "generated" / "MCP_STATUS.md"
            status_path.parent.mkdir(parents=True, exist_ok=True)
            status_path.write_text(content, encoding="utf-8")

            logger.debug("MCP_STATUS.md 已更新")
        except Exception as e:
            logger.warning(f"更新 MCP_STATUS.md 失败: {e}")

    def _generate_tools_md(self, tools: list[BaseTool]) -> str:
        """生成 TOOLS.md 内容.

        Args:
            tools: 工具列表

        Returns:
            Markdown 内容
        """
        lines = ["# 工具文档\n"]

        by_category: dict[str, list[BaseTool]] = {}
        for tool in tools:
            entry = self.registry._tools.get(tool.name)
            category = entry.meta.category.value if entry else "other"
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(tool)

        category_names = {
            "file": "文件操作",
            "memory": "记忆管理",
            "web": "网络工具",
            "shell": "Shell 执行",
            "config": "配置管理",
            "background": "后台任务",
            "schedule": "定时任务",
            "mcp": "MCP 工具",
            "plugin": "插件工具",
        }

        for category, category_tools in sorted(by_category.items()):
            lines.append(f"\n## {category_names.get(category, category)}\n")
            for tool in category_tools:
                lines.append(f"### {tool.name}\n")
                lines.append(f"{tool.description}\n")
                lines.append("\n---\n")

        return "".join(lines)

    def _generate_mcp_status_md(self, status: dict) -> str:
        """生成 MCP_STATUS.md 内容.

        Args:
            status: MCP 状态

        Returns:
            Markdown 内容
        """
        lines = ["# MCP 服务器状态\n\n"]
        lines.append(f"**最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        mcp_tools = self.registry.get_tools_by_source("mcp")

        if not mcp_tools:
            lines.append("当前无 MCP 工具加载。\n")
        else:
            lines.append(f"**已加载工具数**: {len(mcp_tools)}\n\n")
            lines.append("### 已加载的 MCP 工具\n\n")
            for tool in mcp_tools:
                desc = (
                    tool.description[:50] + "..."
                    if len(tool.description) > 50
                    else tool.description
                )
                lines.append(f"- `{tool.name}`: {desc}\n")

        return "".join(lines)

    def _compute_config_hash(self) -> str:
        """计算配置文件哈希.

        Returns:
            配置文件 MD5 哈希值
        """
        mcp_path = self.workspace / "config" / "mcp.json"
        if not mcp_path.exists():
            return ""

        content = mcp_path.read_text(encoding="utf-8")
        return hashlib.md5(content.encode()).hexdigest()

    def check_config_changed(self) -> bool:
        """检查配置是否变化.

        Returns:
            配置是否变化
        """
        return self._compute_config_hash() != self._config_hash

    def get_mcp_status(self) -> dict:
        """获取 MCP 状态.

        Returns:
            MCP 状态字典
        """
        return {
            "connected": self._mcp_connector is not None,
            "tools_count": len(self.registry.get_tools_by_source("mcp")),
            "config_hash": self._config_hash[:8] if self._config_hash else "none",
            "pending_update": self._pending_update,
            "last_update_time": self._last_update_time,
        }

    async def cleanup(self) -> None:
        """清理资源."""
        if self._mcp_connector:
            try:
                await self._mcp_connector.stop()
            except Exception as e:
                logger.warning(f"清理 MCP 资源时出错: {e}")
            self._mcp_connector = None
