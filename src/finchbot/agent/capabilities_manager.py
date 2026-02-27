"""能力描述管理器.

提供动态更新机制，自动检测 MCP 配置变化并更新 CAPABILITIES.md。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from finchbot.config.loader import load_mcp_config
from finchbot.workspace import get_capabilities_path, get_mcp_config_path

if TYPE_CHECKING:
    from finchbot.config.schema import Config


class CapabilitiesManager:
    """能力描述管理器.

    负责管理 CAPABILITIES.md 的生成和更新。
    支持自动检测配置文件变化。

    Attributes:
        workspace: 工作区路径.
        config: FinchBot 配置对象.
        _last_mcp_hash: 上次 MCP 配置的哈希值.
    """

    def __init__(self, workspace: Path, config: Config) -> None:
        """初始化能力管理器.

        Args:
            workspace: 工作区路径.
            config: FinchBot 配置对象.
        """
        self.workspace = workspace
        self.config = config
        self._last_mcp_hash: str | None = None
        self._last_capabilities_hash: str | None = None

    def check_and_update(self) -> bool:
        """检查配置变化并更新 CAPABILITIES.md.

        Returns:
            是否进行了更新.
        """
        mcp_changed = self._check_mcp_config_changed()
        capabilities_stale = self._check_capabilities_stale()

        if mcp_changed or capabilities_stale:
            self.update_capabilities()
            return True

        return False

    def _check_mcp_config_changed(self) -> bool:
        """检查 MCP 配置是否发生变化.

        Returns:
            配置是否发生变化.
        """
        mcp_path = get_mcp_config_path(self.workspace)

        if not mcp_path.exists():
            return self._last_mcp_hash is not None

        try:
            content = mcp_path.read_text(encoding="utf-8")
            current_hash = hashlib.md5(content.encode()).hexdigest()

            if self._last_mcp_hash is None:
                self._last_mcp_hash = current_hash
                return False

            if current_hash != self._last_mcp_hash:
                self._last_mcp_hash = current_hash
                logger.info("MCP configuration changed, updating capabilities")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking MCP config: {e}")
            return False

    def _check_capabilities_stale(self) -> bool:
        """检查 CAPABILITIES.md 是否过期或不存在.

        Returns:
            是否需要更新.
        """
        capabilities_path = get_capabilities_path(self.workspace)

        if not capabilities_path.exists():
            return True

        mcp_path = get_mcp_config_path(self.workspace)

        if not mcp_path.exists():
            return False

        try:
            mcp_mtime = mcp_path.stat().st_mtime
            cap_mtime = capabilities_path.stat().st_mtime

            return mcp_mtime > cap_mtime

        except Exception as e:
            logger.error(f"Error checking capabilities staleness: {e}")
            return False

    def update_capabilities(self) -> Path | None:
        """更新 CAPABILITIES.md 文件.

        Returns:
            生成的文件路径，失败返回 None.
        """
        from finchbot.agent.capabilities import write_capabilities_md

        mcp_servers = load_mcp_config(self.workspace)
        if mcp_servers:
            self.config.mcp.servers = mcp_servers

        try:
            file_path = write_capabilities_md(self.workspace, self.config)
            if file_path:
                logger.info(f"CAPABILITIES.md updated at: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to update CAPABILITIES.md: {e}")
            return None

    def get_current_capabilities(self) -> str:
        """获取当前能力描述内容.

        Returns:
            能力描述文本.
        """
        from finchbot.agent.capabilities import CapabilitiesBuilder

        mcp_servers = load_mcp_config(self.workspace)
        if mcp_servers:
            self.config.mcp.servers = mcp_servers

        builder = CapabilitiesBuilder(self.config)
        return builder.build_capabilities_prompt()

    def get_mcp_servers_info(self) -> dict:
        """获取当前 MCP 服务器信息.

        Returns:
            MCP 服务器信息字典.
        """
        mcp_servers = load_mcp_config(self.workspace)

        info = {
            "count": len(mcp_servers),
            "servers": {},
        }

        for name, config in mcp_servers.items():
            info["servers"][name] = {
                "type": "stdio" if config.command else "http",
                "disabled": config.disabled,
                "command": config.command if config.command else None,
                "url": config.url if config.url else None,
            }

        return info

    def initialize(self) -> None:
        """初始化能力管理器.

        加载当前配置状态，但不生成文件。
        """
        mcp_path = get_mcp_config_path(self.workspace)

        if mcp_path.exists():
            try:
                content = mcp_path.read_text(encoding="utf-8")
                self._last_mcp_hash = hashlib.md5(content.encode()).hexdigest()
            except Exception as e:
                logger.error(f"Error initializing capabilities manager: {e}")

        capabilities_path = get_capabilities_path(self.workspace)

        if capabilities_path.exists():
            try:
                content = capabilities_path.read_text(encoding="utf-8")
                self._last_capabilities_hash = hashlib.md5(content.encode()).hexdigest()
            except Exception as e:
                logger.error(f"Error reading capabilities file: {e}")


_capabilities_manager: CapabilitiesManager | None = None


def get_capabilities_manager(workspace: Path, config: Config) -> CapabilitiesManager:
    """获取能力管理器实例.

    Args:
        workspace: 工作区路径.
        config: FinchBot 配置对象.

    Returns:
        能力管理器实例.
    """
    global _capabilities_manager

    if _capabilities_manager is None:
        _capabilities_manager = CapabilitiesManager(workspace, config)
        _capabilities_manager.initialize()

    return _capabilities_manager


def reset_capabilities_manager() -> None:
    """重置能力管理器实例.

    用于测试或强制重新初始化。
    """
    global _capabilities_manager
    _capabilities_manager = None
