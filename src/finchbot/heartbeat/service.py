"""心跳服务.

定期唤醒 Agent 检查是否有待处理任务，通过 LLM 决定是否执行。
支持结果通知回调。
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from finchbot.i18n import t

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


_HEARTBEAT_TOOL = {
    "type": "function",
    "function": {
        "name": "heartbeat",
        "description": "Report your decision about pending tasks",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["skip", "run"],
                    "description": "skip if no pending tasks, run if there are tasks to execute",
                },
                "tasks": {
                    "type": "string",
                    "description": "Description of tasks to run (required if action is run)",
                },
            },
            "required": ["action"],
        },
    },
}


class HeartbeatService:
    """心跳服务.

    定期检查 HEARTBEAT.md 文件，通过 LLM 决定是否执行任务。
    作为后台服务运行，随 chat 会话启动和停止。
    支持结果通知回调。

    Attributes:
        workspace: 工作目录
        model: LLM 模型
        on_execute: 执行回调
        on_notify: 通知回调
        interval_s: 检查间隔（秒）
        enabled: 是否启用
    """

    def __init__(
        self,
        workspace: Path,
        model: BaseChatModel,
        on_execute: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        on_notify: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        interval_s: int = 1800,
        enabled: bool = True,
    ) -> None:
        """初始化心跳服务.

        Args:
            workspace: 工作目录
            model: LLM 模型
            on_execute: 执行回调（接收任务描述，返回执行结果）
            on_notify: 通知回调（接收执行结果，用于通知用户）
            interval_s: 检查间隔（秒），默认 30 分钟
            enabled: 是否启用
        """
        self.workspace = workspace
        self.model = model
        self.on_execute = on_execute
        self.on_notify = on_notify
        self.interval_s = interval_s
        self.enabled = enabled
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_check: datetime | None = None
        self._next_check: datetime | None = None

    @property
    def heartbeat_file(self) -> Path:
        """心跳文件路径."""
        return self.workspace / "HEARTBEAT.md"

    async def start(self) -> None:
        """启动心跳服务."""
        if not self.enabled:
            logger.info(t("heartbeat.disabled"))
            return

        if self._running:
            logger.warning("Heartbeat already running")
            return

        self._running = True
        self._update_next_check()
        self._task = asyncio.create_task(self._loop())
        logger.info(t("heartbeat.service_started", interval=self.interval_s))

    async def stop(self) -> None:
        """停止心跳服务."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info(t("heartbeat.service_stopped"))

    async def trigger(self) -> tuple[str, str]:
        """手动触发一次心跳检查.

        Returns:
            (action, tasks) 元组
        """
        return await self._tick()

    def get_status(self) -> dict:
        """获取服务状态.

        Returns:
            状态字典
        """
        return {
            "enabled": self.enabled,
            "running": self._running,
            "interval_s": self.interval_s,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "next_check": self._next_check.isoformat() if self._next_check else None,
            "file_exists": self.heartbeat_file.exists(),
        }

    def _update_next_check(self) -> None:
        """更新下次检查时间."""
        if self._last_check:
            self._next_check = datetime.fromtimestamp(
                self._last_check.timestamp() + self.interval_s,
                tz=UTC,
            )
        else:
            self._next_check = datetime.fromtimestamp(
                datetime.now(UTC).timestamp() + self.interval_s,
                tz=UTC,
            )

    async def _loop(self) -> None:
        """心跳循环."""
        while self._running:
            try:
                await asyncio.sleep(self.interval_s)
                if self._running:
                    await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _tick(self) -> tuple[str, str]:
        """执行一次心跳检查.

        Returns:
            (action, tasks) 元组
        """
        self._last_check = datetime.now(UTC)
        self._update_next_check()

        if not self.heartbeat_file.exists():
            logger.debug(t("heartbeat.no_file"))
            return "skip", ""

        content = self.heartbeat_file.read_text(encoding="utf-8").strip()
        if not content:
            logger.debug(t("heartbeat.empty_file"))
            return "skip", ""

        action, tasks = await self._decide(content)

        if action == "run" and tasks:
            logger.info(t("heartbeat.run", tasks=tasks))
            if self.on_execute:
                try:
                    result = await self.on_execute(tasks)
                    logger.info(f"Heartbeat execution result: {result[:100]}...")

                    if result and self.on_notify:
                        try:
                            await self.on_notify(result)
                            logger.info("Heartbeat result notified")
                        except Exception as e:
                            logger.error(f"Heartbeat notify failed: {e}")

                except Exception as e:
                    logger.error(f"Heartbeat execution failed: {e}")
        else:
            logger.debug(t("heartbeat.skip"))

        return action, tasks

    async def _decide(self, content: str) -> tuple[str, str]:
        """通过 LLM 决定是否执行任务.

        Args:
            content: HEARTBEAT.md 文件内容

        Returns:
            (action, tasks) 元组
        """
        try:
            response = await self.model.ainvoke(
                [
                    SystemMessage(content=t("heartbeat.system_prompt")),
                    HumanMessage(content=t("heartbeat.user_prompt", content=content)),
                ],
                tools=[_HEARTBEAT_TOOL],
                tool_choice={"type": "function", "function": {"name": "heartbeat"}},
            )

            if response.tool_calls:
                tc = response.tool_calls[0]
                args = tc.get("args", {})
                action = args.get("action", "skip")
                tasks = args.get("tasks", "")
                return action, tasks

        except Exception as e:
            logger.error(f"Heartbeat decision failed: {e}")

        return "skip", ""

    def create_heartbeat_file(self, content: str = "") -> None:
        """创建心跳文件.

        Args:
            content: 初始内容（可选）
        """
        if not self.heartbeat_file.exists():
            default_content = content or t("heartbeat.default_content")
            self.heartbeat_file.write_text(default_content, encoding="utf-8")
            logger.info(f"Created heartbeat file: {self.heartbeat_file}")
