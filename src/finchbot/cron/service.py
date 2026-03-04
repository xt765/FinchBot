"""定时任务调度服务.

参考 nanobot 设计，支持三种调度模式：
- at: 一次性任务
- every: 间隔任务
- cron: cron 表达式（支持时区）

特性：
- 毫秒级时间戳精度
- 时区支持
- 任务状态跟踪
- 外部文件修改检测
- 消息投递支持
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable, Coroutine
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from finchbot.cron.types import (
    CronJob,
    CronJobState,
    CronPayload,
    CronSchedule,
    CronStore,
    now_ms,
)
from finchbot.i18n import t

if TYPE_CHECKING:
    pass


def _compute_next_run(schedule: CronSchedule, now_ms_val: int) -> int | None:
    """计算下次执行时间.

    Args:
        schedule: 调度配置
        now_ms_val: 当前时间戳（毫秒）

    Returns:
        下次执行时间戳（毫秒），无效配置返回 None
    """
    if schedule.kind == "at":
        return schedule.at_ms if schedule.at_ms and schedule.at_ms > now_ms_val else None

    if schedule.kind == "every":
        if not schedule.every_ms or schedule.every_ms <= 0:
            return None
        return now_ms_val + schedule.every_ms

    if schedule.kind == "cron" and schedule.expr:
        try:
            from zoneinfo import ZoneInfo

            from croniter import croniter

            base_time = now_ms_val / 1000
            tz = ZoneInfo(schedule.tz) if schedule.tz else datetime.now().astimezone().tzinfo
            base_dt = datetime.fromtimestamp(base_time, tz=tz)
            cron = croniter(schedule.expr, base_dt)
            next_dt = cron.get_next(datetime)
            return int(next_dt.timestamp() * 1000)
        except Exception as e:
            logger.error(f"Failed to compute next run for cron '{schedule.expr}': {e}")
            return None

    return None


class CronService:
    """定时任务调度服务.

    支持三种调度模式、时区、状态跟踪和消息投递。

    Attributes:
        store_path: 存储文件路径
        on_job: 任务执行回调
        on_deliver: 消息投递回调
        _store: 任务存储
        _last_mtime: 上次文件修改时间
        _timer_task: 定时器任务
        _running: 是否运行中
    """

    def __init__(
        self,
        store_path: Path,
        on_job: Callable[[CronJob], Coroutine[Any, Any, str | None]] | None = None,
        on_deliver: Callable[[str, str, str], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """初始化服务.

        Args:
            store_path: 存储目录路径
            on_job: 任务执行回调
            on_deliver: 消息投递回调 (channel, target_id, message)
        """
        self.store_path = store_path / "cron" / "jobs.json"
        self.on_job = on_job
        self.on_deliver = on_deliver
        self._store: CronStore | None = None
        self._last_mtime: float = 0.0
        self._timer_task: asyncio.Task | None = None
        self._running = False

    def _load_store(self) -> CronStore:
        """加载任务存储.

        如果文件被外部修改，自动重新加载。

        Returns:
            任务存储对象
        """
        if self._store and self.store_path.exists():
            mtime = self.store_path.stat().st_mtime
            if mtime != self._last_mtime:
                logger.info("Cron: jobs.json modified externally, reloading")
                self._store = None

        if self._store:
            return self._store

        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                jobs = []
                for j in data.get("jobs", []):
                    jobs.append(
                        CronJob(
                            id=j["id"],
                            name=j["name"],
                            enabled=j.get("enabled", True),
                            schedule=CronSchedule(
                                kind=j["schedule"]["kind"],
                                at_ms=j["schedule"].get("atMs"),
                                every_ms=j["schedule"].get("everyMs"),
                                expr=j["schedule"].get("expr"),
                                tz=j["schedule"].get("tz"),
                            ),
                            payload=CronPayload(
                                kind=j["payload"].get("kind", "agent_turn"),
                                message=j["payload"].get("message", ""),
                                deliver=j["payload"].get("deliver", False),
                                channel=j["payload"].get("channel"),
                                to=j["payload"].get("to"),
                            ),
                            state=CronJobState(
                                next_run_at_ms=j.get("state", {}).get("nextRunAtMs"),
                                last_run_at_ms=j.get("state", {}).get("lastRunAtMs"),
                                last_status=j.get("state", {}).get("lastStatus"),
                                last_error=j.get("state", {}).get("lastError"),
                            ),
                            created_at_ms=j.get("createdAtMs", 0),
                            updated_at_ms=j.get("updatedAtMs", 0),
                            delete_after_run=j.get("deleteAfterRun", False),
                        )
                    )
                self._store = CronStore(jobs=jobs)
            except Exception as e:
                logger.warning(f"Failed to load cron store: {e}")
                self._store = CronStore()
        else:
            self._store = CronStore()

        return self._store

    def _save_store(self) -> None:
        """保存任务存储到文件."""
        if not self._store:
            return

        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self._store.version,
            "jobs": [
                {
                    "id": j.id,
                    "name": j.name,
                    "enabled": j.enabled,
                    "schedule": {
                        "kind": j.schedule.kind,
                        "atMs": j.schedule.at_ms,
                        "everyMs": j.schedule.every_ms,
                        "expr": j.schedule.expr,
                        "tz": j.schedule.tz,
                    },
                    "payload": {
                        "kind": j.payload.kind,
                        "message": j.payload.message,
                        "deliver": j.payload.deliver,
                        "channel": j.payload.channel,
                        "to": j.payload.to,
                    },
                    "state": {
                        "nextRunAtMs": j.state.next_run_at_ms,
                        "lastRunAtMs": j.state.last_run_at_ms,
                        "lastStatus": j.state.last_status,
                        "lastError": j.state.last_error,
                    },
                    "createdAtMs": j.created_at_ms,
                    "updatedAtMs": j.updated_at_ms,
                    "deleteAfterRun": j.delete_after_run,
                }
                for j in self._store.jobs
            ],
        }

        self.store_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self._last_mtime = self.store_path.stat().st_mtime

    async def start(self) -> None:
        """启动服务."""
        self._running = True
        self._load_store()
        self._recompute_next_runs()
        self._save_store()

        try:
            self._arm_timer()
            job_count = len(self._store.jobs) if self._store else 0
            logger.info(t("cron.service_started", count=job_count))
        except RuntimeError as e:
            logger.warning(f"CronService: Failed to arm timer: {e}")
            self._running = False

    async def stop(self) -> None:
        """停止服务."""
        self._running = False
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None
        logger.info(t("cron.service_stopped"))

    def _recompute_next_runs(self) -> None:
        """重新计算所有启用任务的下次执行时间."""
        if not self._store:
            return
        current_ms = now_ms()
        for job in self._store.jobs:
            if job.enabled:
                job.state.next_run_at_ms = _compute_next_run(job.schedule, current_ms)

    def _get_next_wake_ms(self) -> int | None:
        """获取最近的下次执行时间.

        Returns:
            最近的执行时间戳，无任务返回 None
        """
        if not self._store:
            return None
        times = [
            j.state.next_run_at_ms for j in self._store.jobs if j.enabled and j.state.next_run_at_ms
        ]
        return min(times) if times else None

    def _arm_timer(self) -> None:
        """设置定时器."""
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None

        next_wake = self._get_next_wake_ms()
        if not next_wake or not self._running:
            return

        delay_ms = max(0, next_wake - now_ms())
        delay_s = delay_ms / 1000

        async def tick() -> None:
            await asyncio.sleep(delay_s)
            if self._running:
                await self._on_timer()

        try:
            # Python 3.13+ 不再支持 loop 参数
            self._timer_task = asyncio.create_task(tick())
        except RuntimeError:
            # 没有运行中的事件循环，定时器将在服务启动时设置
            logger.debug("CronService: No running event loop, timer will be armed on next start")
            pass

    async def _on_timer(self) -> None:
        """定时器回调 - 执行到期任务."""
        if not self._store:
            return

        current_ms = now_ms()
        due_jobs = [
            j
            for j in self._store.jobs
            if j.enabled and j.state.next_run_at_ms and current_ms >= j.state.next_run_at_ms
        ]

        for job in due_jobs:
            await self._execute_job(job)

        self._save_store()
        self._arm_timer()

    async def _execute_job(self, job: CronJob) -> None:
        """执行单个任务.

        Args:
            job: 任务对象
        """
        start_ms = now_ms()
        logger.info(t("cron.executing", name=job.name, id=job.id))

        response = None
        try:
            if self.on_job:
                response = await self.on_job(job)

            job.state.last_status = "ok"
            job.state.last_error = None
            logger.info(t("cron.execute_success", name=job.name))

        except Exception as e:
            job.state.last_status = "error"
            job.state.last_error = str(e)
            logger.error(t("cron.execute_failed", name=job.name, error=str(e)))

        job.state.last_run_at_ms = start_ms
        job.updated_at_ms = now_ms()

        if (
            job.payload.deliver
            and job.payload.channel
            and job.payload.to
            and response
            and self.on_deliver
        ):
            try:
                await self.on_deliver(job.payload.channel, job.payload.to, response)
                logger.info(
                    f"Cron job '{job.name}' result delivered to {job.payload.channel}:{job.payload.to}"
                )
            except Exception as e:
                logger.error(f"Failed to deliver cron job result: {e}")

        if job.schedule.kind == "at":
            if job.delete_after_run:
                store = self._load_store()
                store.jobs = [j for j in store.jobs if j.id != job.id]
                self._save_store()
            else:
                job.enabled = False
                job.state.next_run_at_ms = None
        else:
            job.state.next_run_at_ms = _compute_next_run(job.schedule, now_ms())

    def list_jobs(self, include_disabled: bool = False) -> list[CronJob]:
        """列出所有任务.

        Args:
            include_disabled: 是否包含已禁用的任务

        Returns:
            任务列表
        """
        store = self._load_store()
        jobs = store.jobs if include_disabled else [j for j in store.jobs if j.enabled]
        return sorted(jobs, key=lambda j: j.state.next_run_at_ms or float("inf"))

    def add_job(
        self,
        name: str,
        schedule: CronSchedule,
        message: str,
        deliver: bool = False,
        channel: str | None = None,
        to: str | None = None,
        delete_after_run: bool = False,
    ) -> CronJob:
        """添加新任务.

        Args:
            name: 任务名称
            schedule: 调度配置
            message: 任务消息
            deliver: 是否投递响应
            channel: 投递渠道
            to: 投递目标
            delete_after_run: 执行后是否删除

        Returns:
            创建的任务对象
        """
        store = self._load_store()
        schedule.validate()
        current_ms = now_ms()

        job = CronJob(
            id=str(uuid.uuid4())[:8],
            name=name,
            enabled=True,
            schedule=schedule,
            payload=CronPayload(
                kind="agent_turn",
                message=message,
                deliver=deliver,
                channel=channel,
                to=to,
            ),
            state=CronJobState(next_run_at_ms=_compute_next_run(schedule, current_ms)),
            created_at_ms=current_ms,
            updated_at_ms=current_ms,
            delete_after_run=delete_after_run,
        )

        store.jobs.append(job)
        self._save_store()

        # 尝试设置定时器，如果没有事件循环则跳过（服务启动时会重新设置）
        self._try_arm_timer()

        logger.info(t("cron.job_created", id=job.id, schedule=schedule.expr or schedule.kind))
        return job

    def _try_arm_timer(self) -> None:
        """尝试设置定时器，处理没有事件循环的情况."""
        try:
            self._arm_timer()
        except RuntimeError:
            # 没有运行中的事件循环，定时器将在服务启动时设置
            logger.debug(
                "CronService: Cannot arm timer without event loop, will be armed on next start"
            )

    def remove_job(self, job_id: str) -> bool:
        """删除任务.

        Args:
            job_id: 任务 ID

        Returns:
            是否成功删除
        """
        store = self._load_store()
        before = len(store.jobs)
        store.jobs = [j for j in store.jobs if j.id != job_id]
        removed = len(store.jobs) < before

        if removed:
            self._save_store()
            self._try_arm_timer()
            logger.info(t("cron.job_deleted", id=job_id))

        return removed

    def enable_job(self, job_id: str, enabled: bool = True) -> CronJob | None:
        """启用或禁用任务.

        Args:
            job_id: 任务 ID
            enabled: 是否启用

        Returns:
            更新后的任务，不存在返回 None
        """
        store = self._load_store()
        for job in store.jobs:
            if job.id == job_id:
                job.enabled = enabled
                job.updated_at_ms = now_ms()
                if enabled:
                    job.state.next_run_at_ms = _compute_next_run(job.schedule, now_ms())
                else:
                    job.state.next_run_at_ms = None
                self._save_store()
                self._try_arm_timer()
                return job
        return None

    async def run_job(self, job_id: str, force: bool = False) -> bool:
        """手动执行任务.

        Args:
            job_id: 任务 ID
            force: 是否强制执行（忽略禁用状态）

        Returns:
            是否成功执行
        """
        store = self._load_store()
        for job in store.jobs:
            if job.id == job_id:
                if not force and not job.enabled:
                    return False
                await self._execute_job(job)
                self._save_store()
                self._try_arm_timer()
                return True
        return False

    def get_job(self, job_id: str) -> CronJob | None:
        """获取单个任务.

        Args:
            job_id: 任务 ID

        Returns:
            任务对象，不存在返回 None
        """
        store = self._load_store()
        for job in store.jobs:
            if job.id == job_id:
                return job
        return None

    def status(self) -> dict:
        """获取服务状态.

        Returns:
            状态字典
        """
        store = self._load_store()
        return {
            "enabled": self._running,
            "jobs": len(store.jobs),
            "next_wake_at_ms": self._get_next_wake_ms(),
        }

    def get_pending_jobs(self) -> list[CronJob]:
        """获取待处理的定时任务.

        返回下次执行时间在当前时间之前的任务。

        Returns:
            待处理任务列表
        """
        store = self._load_store()
        current_ms = now_ms()
        pending = []

        for job in store.jobs:
            if not job.enabled:
                continue
            if job.state.next_run_at_ms and job.state.next_run_at_ms <= current_ms:
                pending.append(job)

        return pending

    def get_next_jobs(self, count: int = 5) -> list[CronJob]:
        """获取即将执行的任务.

        Args:
            count: 返回数量

        Returns:
            按执行时间排序的任务列表
        """
        store = self._load_store()
        jobs = [job for job in store.jobs if job.enabled and job.state.next_run_at_ms]
        jobs.sort(key=lambda j: j.state.next_run_at_ms or 0)
        return jobs[:count]

    def get_job_summary(self) -> dict:
        """获取任务摘要.

        Returns:
            任务摘要字典
        """
        store = self._load_store()
        next_runs = [j.state.next_run_at_ms for j in store.jobs if j.state.next_run_at_ms]
        return {
            "total": len(store.jobs),
            "enabled": sum(1 for j in store.jobs if j.enabled),
            "disabled": sum(1 for j in store.jobs if not j.enabled),
            "next_run": min(next_runs) if next_runs else None,
        }
