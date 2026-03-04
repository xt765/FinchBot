"""统一服务管理器.

管理所有后台服务的生命周期，支持热更新。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from finchbot.services.config import ServiceConfig

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import BaseTool

    from finchbot.config.schema import Config
    from finchbot.tools.core import ToolRegistry


class ServiceManager:
    """统一服务管理器.

    管理所有后台服务的生命周期：
    - CronService: 定时任务调度
    - HeartbeatService: 心跳监控
    - SubagentManager: 子代理管理
    - JobManager: 后台任务管理

    所有服务共享同一个 ToolRegistry，支持工具热更新。

    Attributes:
        workspace: 工作区路径
        config: 配置对象
        registry: 工具注册表
        model: 语言模型
        service_config: 服务配置
        _services: 服务实例映射
        _running: 是否运行中
    """

    _instance: ServiceManager | None = None

    def __init__(
        self,
        workspace: Path,
        config: Config,
        registry: ToolRegistry,
        model: BaseChatModel,
        service_config: ServiceConfig | None = None,
    ) -> None:
        """初始化服务管理器.

        Args:
            workspace: 工作区路径
            config: 配置对象
            registry: 工具注册表
            model: 语言模型
            service_config: 服务配置
        """
        self.workspace = workspace
        self.config = config
        self.registry = registry
        self.model = model
        self.service_config = service_config or ServiceConfig()

        self._services: dict[str, Any] = {}
        self._running = False
        self._on_tool_update_callbacks: list[Callable[[list], None]] = []
        self._on_cron_deliver: Callable[[str, str, str], Any] | None = None
        self._on_subagent_notify: Callable[[str, str, str], Any] | None = None

    @classmethod
    def get_instance(cls) -> ServiceManager | None:
        """获取单例实例."""
        return cls._instance

    @classmethod
    def set_instance(cls, instance: ServiceManager) -> None:
        """设置单例实例."""
        cls._instance = instance

    def on_tool_update(self, callback: Callable[[list], None]) -> None:
        """注册工具更新回调.

        Args:
            callback: 回调函数
        """
        self._on_tool_update_callbacks.append(callback)

    async def start_all(self) -> None:
        """启动所有服务."""
        if self._running:
            return

        logger.info("启动所有后台服务...")

        if self.service_config.cron_enabled:
            await self._start_cron_service()

        if self.service_config.heartbeat_enabled:
            await self._start_heartbeat_service()

        await self._start_subagent_manager()

        await self._start_job_manager()

        self._running = True
        logger.info("所有后台服务已启动")

    async def stop_all(self) -> None:
        """停止所有服务."""
        if not self._running:
            return

        logger.info("停止所有后台服务...")

        if "job_manager" in self._services:
            await self._stop_job_manager()

        if "subagent_manager" in self._services:
            await self._stop_subagent_manager()

        if "heartbeat" in self._services:
            await self._stop_heartbeat_service()

        if "cron" in self._services:
            await self._stop_cron_service()

        self._running = False
        logger.info("所有后台服务已停止")

    async def _start_cron_service(self) -> None:
        """启动定时任务服务."""
        try:
            from finchbot.cron import CronService

            cron = CronService(
                store_path=self.workspace / "data",
                on_job=self._on_cron_job,
                on_deliver=self._on_cron_deliver,
            )
            await cron.start()
            self._services["cron"] = cron
            logger.info("CronService 已启动")
        except Exception as e:
            logger.error(f"启动 CronService 失败: {e}")

    async def _stop_cron_service(self) -> None:
        """停止定时任务服务."""
        if "cron" in self._services:
            await self._services["cron"].stop()
            del self._services["cron"]
            logger.info("CronService 已停止")

    async def _start_heartbeat_service(self) -> None:
        """启动心跳服务."""
        try:
            from finchbot.heartbeat import HeartbeatService

            heartbeat = HeartbeatService(
                workspace=self.workspace,
                model=self.model,
                on_execute=self._on_heartbeat_execute,
                on_notify=self._on_heartbeat_notify,
                interval_s=self.service_config.heartbeat_interval_s,
            )
            await heartbeat.start()
            self._services["heartbeat"] = heartbeat
            logger.info("HeartbeatService 已启动")
        except Exception as e:
            logger.error(f"启动 HeartbeatService 失败: {e}")

    async def _stop_heartbeat_service(self) -> None:
        """停止心跳服务."""
        if "heartbeat" in self._services:
            await self._services["heartbeat"].stop()
            del self._services["heartbeat"]
            logger.info("HeartbeatService 已停止")

    async def _start_subagent_manager(self) -> None:
        """启动子代理管理器."""
        try:
            from finchbot.agent.subagent import SubagentManager

            tools = self.registry.get_tools()
            subagent = SubagentManager(
                model=self.model,
                workspace=self.workspace,
                tools=tools,
                on_notify=self._on_subagent_notify,
            )
            self._services["subagent_manager"] = subagent
            logger.info(f"SubagentManager 已启动，工具数: {len(tools)}")
        except Exception as e:
            logger.error(f"启动 SubagentManager 失败: {e}")

    async def _stop_subagent_manager(self) -> None:
        """停止子代理管理器."""
        if "subagent_manager" in self._services:
            await self._services["subagent_manager"].cancel_all()
            del self._services["subagent_manager"]
            logger.info("SubagentManager 已停止")

    async def _start_job_manager(self) -> None:
        """启动后台任务管理器."""
        try:
            from finchbot.agent.tools.background import JobManager

            job_manager = JobManager()
            if "subagent_manager" in self._services:
                job_manager.set_subagent_manager(self._services["subagent_manager"])
            self._services["job_manager"] = job_manager
            logger.info("JobManager 已启动")
        except Exception as e:
            logger.error(f"启动 JobManager 失败: {e}")

    async def _stop_job_manager(self) -> None:
        """停止后台任务管理器."""
        if "job_manager" in self._services:
            self._services["job_manager"].clear_all()
            del self._services["job_manager"]
            logger.info("JobManager 已停止")

    async def update_tools(self, new_tools: list[BaseTool]) -> None:
        """更新所有服务的工具列表.

        当 MCP 工具热更新时调用。

        Args:
            new_tools: 新的工具列表
        """
        if "subagent_manager" in self._services:
            self._services["subagent_manager"].update_tools(new_tools)
            logger.info(f"SubagentManager 工具已更新: {len(new_tools)} 个")

        for callback in self._on_tool_update_callbacks:
            try:
                callback(new_tools)
            except Exception as e:
                logger.warning(f"工具更新回调失败: {e}")

    def get_cron_service(self):
        """获取定时任务服务.

        Returns:
            CronService 实例
        """
        return self._services.get("cron")

    def get_subagent_manager(self):
        """获取子代理管理器.

        Returns:
            SubagentManager 实例
        """
        return self._services.get("subagent_manager")

    def get_job_manager(self):
        """获取后台任务管理器.

        Returns:
            JobManager 实例
        """
        return self._services.get("job_manager")

    def get_heartbeat_service(self):
        """获取心跳服务.

        Returns:
            HeartbeatService 实例
        """
        return self._services.get("heartbeat")

    @property
    def is_running(self) -> bool:
        """是否正在运行."""
        return self._running

    def get_status(self) -> dict[str, Any]:
        """获取服务状态.

        Returns:
            服务状态字典
        """
        return {
            "running": self._running,
            "services": {
                "cron": "cron" in self._services,
                "heartbeat": "heartbeat" in self._services,
                "subagent_manager": "subagent_manager" in self._services,
                "job_manager": "job_manager" in self._services,
            },
            "tool_count": self.registry.count(enabled_only=True),
        }

    async def _on_cron_job(self, job: Any) -> None:
        """定时任务执行回调.

        Args:
            job: 定时任务
        """
        logger.debug(f"执行定时任务: {job.name}")

    async def _on_cron_deliver(self, channel: str, to: str, message: str) -> None:
        """定时任务消息投递回调.

        Args:
            channel: 投递渠道
            to: 投递目标
            message: 消息内容
        """
        logger.debug(f"投递消息: {channel}:{to}")
        if self._on_cron_deliver:
            try:
                import asyncio

                if asyncio.iscoroutinefunction(self._on_cron_deliver):
                    await self._on_cron_deliver(channel, to, message)
                else:
                    self._on_cron_deliver(channel, to, message)
            except Exception as e:
                logger.error(f"投递消息失败: {e}")

    async def _on_heartbeat_execute(self, task: str) -> None:
        """心跳执行回调.

        Args:
            task: 任务描述
        """
        logger.debug(f"心跳执行任务: {task}")

    async def _on_heartbeat_notify(self, message: str) -> None:
        """心跳通知回调.

        Args:
            message: 通知消息
        """
        logger.debug(f"心跳通知: {message}")

    async def _on_subagent_notify(self, session_key: str, label: str, result: str) -> None:
        """子代理通知回调.

        Args:
            session_key: 会话标识
            label: 任务标签
            result: 执行结果
        """
        logger.debug(f"子代理通知: {label}")
        if self._on_subagent_notify:
            try:
                import asyncio

                if asyncio.iscoroutinefunction(self._on_subagent_notify):
                    await self._on_subagent_notify(session_key, label, result)
                else:
                    self._on_subagent_notify(session_key, label, result)
            except Exception as e:
                logger.error(f"子代理通知失败: {e}")
