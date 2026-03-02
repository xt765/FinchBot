"""定时任务调度服务.

提供与 LangGraph Cloud Cron API 兼容的本地实现。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from croniter import croniter
from loguru import logger
from pydantic import BaseModel, Field

from finchbot.i18n import t

if TYPE_CHECKING:
    pass


class CronJob(BaseModel):
    """定时任务."""

    cron_id: str
    name: str
    schedule: str  # cron 表达式
    message: str  # 任务内容
    input: dict = Field(default_factory=dict)
    enabled: bool = True
    next_run_date: str | None = None
    last_run_date: str | None = None
    run_count: int = 0
    metadata: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CronService:
    """定时任务调度服务.

    与 LangGraph Cloud Cron API 兼容的本地实现。

    Attributes:
        store_path: 存储路径
        _jobs: 任务映射
        _timer_task: 定时器任务
        _on_job: 任务回调
        _running: 是否运行中
    """

    def __init__(self, store_path: Path) -> None:
        """初始化服务.

        Args:
            store_path: 存储目录路径
        """
        self.store_path = store_path / "cron" / "jobs.json"
        self._jobs: dict[str, CronJob] = {}
        self._timer_task: asyncio.Task | None = None
        self._on_job: Callable[[CronJob], Any] | None = None
        self._running = False

    async def create(
        self,
        name: str,
        schedule: str,
        message: str,
        input: dict | None = None,
        metadata: dict | None = None,
    ) -> CronJob:
        """创建定时任务.

        与 LangGraph Cloud API 兼容。

        Args:
            name: 任务名称
            schedule: cron 表达式
            message: 任务内容
            input: 输入数据（可选）
            metadata: 元数据（可选）

        Returns:
            创建的任务
        """
        import uuid

        # 验证 cron 表达式
        try:
            croniter(schedule)
        except Exception as e:
            raise ValueError(f"Invalid cron expression: {schedule}") from e

        job = CronJob(
            cron_id=str(uuid.uuid4())[:8],
            name=name,
            schedule=schedule,
            message=message,
            input=input or {},
            metadata=metadata or {},
        )

        # 计算下次执行时间
        job.next_run_date = self._compute_next_run(schedule)

        self._jobs[job.cron_id] = job
        self._save()

        # 重新设置定时器
        if self._running:
            self._arm_timer()

        logger.info(t("cron.job_created", id=job.cron_id, schedule=schedule))
        return job

    async def delete(self, cron_id: str) -> bool:
        """删除定时任务.

        Args:
            cron_id: 任务 ID

        Returns:
            是否成功删除
        """
        if cron_id in self._jobs:
            del self._jobs[cron_id]
            self._save()
            logger.info(t("cron.job_deleted", id=cron_id))
            return True
        return False

    async def get(self, cron_id: str) -> CronJob | None:
        """获取单个任务.

        Args:
            cron_id: 任务 ID

        Returns:
            任务对象，不存在则返回 None
        """
        return self._jobs.get(cron_id)

    async def list(self, include_disabled: bool = True) -> list[CronJob]:
        """列出所有任务.

        Args:
            include_disabled: 是否包含已禁用的任务

        Returns:
            任务列表
        """
        jobs = list(self._jobs.values())
        if not include_disabled:
            jobs = [j for j in jobs if j.enabled]
        return sorted(jobs, key=lambda j: j.next_run_date or "")

    async def toggle(self, cron_id: str, enabled: bool) -> CronJob | None:
        """启用或禁用任务.

        Args:
            cron_id: 任务 ID
            enabled: 是否启用

        Returns:
            更新后的任务，不存在则返回 None
        """
        job = self._jobs.get(cron_id)
        if job:
            job.enabled = enabled
            if enabled:
                job.next_run_date = self._compute_next_run(job.schedule)
            self._save()
        return job

    async def run_now(self, cron_id: str) -> str | None:
        """立即执行任务.

        Args:
            cron_id: 任务 ID

        Returns:
            执行结果，不存在则返回 None
        """
        job = self._jobs.get(cron_id)
        if not job:
            return None

        logger.info(t("cron.executing", name=job.name, id=job.cron_id))

        try:
            if self._on_job:
                result = await self._on_job(job)
            else:
                result = f"Executed: {job.message}"

            job.run_count += 1
            job.last_run_date = datetime.now(timezone.utc).isoformat()
            job.next_run_date = self._compute_next_run(job.schedule)
            self._save()

            logger.info(t("cron.execute_success", name=job.name))
            return result

        except Exception as e:
            logger.error(t("cron.execute_failed", name=job.name, error=str(e)))
            return f"Error: {e}"

    def on_job(self, callback: Callable[[CronJob], Any]) -> None:
        """设置任务回调.

        Args:
            callback: 回调函数
        """
        self._on_job = callback

    async def start(self) -> None:
        """启动服务."""
        self._running = True
        self._load()
        self._recompute_next_runs()
        self._save()
        self._arm_timer()
        logger.info(t("cron.service_started", count=len(self._jobs)))

    async def stop(self) -> None:
        """停止服务."""
        self._running = False
        if self._timer_task:
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass
        logger.info(t("cron.service_stopped"))

    def _compute_next_run(self, schedule: str) -> str:
        """计算下次执行时间.

        Args:
            schedule: cron 表达式

        Returns:
            ISO 格式的时间字符串（UTC）
        """
        now_local = datetime.now().astimezone()
        cron = croniter(schedule, now_local)
        next_dt_local = cron.get_next(datetime)
        return next_dt_local.astimezone(timezone.utc).isoformat()

    def _recompute_next_runs(self) -> None:
        """重新计算所有任务的下次执行时间."""
        now_local = datetime.now().astimezone()
        for job in self._jobs.values():
            if job.enabled:
                try:
                    cron = croniter(job.schedule, now_local)
                    next_dt_local = cron.get_next(datetime)
                    job.next_run_date = next_dt_local.astimezone(timezone.utc).isoformat()
                except Exception:
                    pass

    def _load(self) -> None:
        """加载任务存储."""
        if self.store_path.exists():
            try:
                with open(self.store_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._jobs = {k: CronJob(**v) for k, v in data.items()}
            except Exception as e:
                logger.warning(f"Failed to load cron store: {e}")
                self._jobs = {}

    def _save(self) -> None:
        """保存任务存储."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.model_dump() for k, v in self._jobs.items()}, f, indent=2, ensure_ascii=False
            )

    def _arm_timer(self) -> None:
        """设置定时器."""
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None

        # 找到最近的待执行任务
        now = datetime.now(timezone.utc)
        enabled_jobs = [j for j in self._jobs.values() if j.enabled and j.next_run_date]

        if not enabled_jobs:
            return

        next_job = min(enabled_jobs, key=lambda j: j.next_run_date or "")
        next_run = datetime.fromisoformat(next_job.next_run_date.replace("Z", "+00:00"))
        delay = (next_run - now).total_seconds()

        if delay > 0:
            self._timer_task = asyncio.create_task(self._timer_callback(delay))

    async def _timer_callback(self, delay: float) -> None:
        """定时器回调.

        Args:
            delay: 延迟秒数
        """
        try:
            await asyncio.sleep(delay)

            if not self._running:
                return

            now = datetime.now(timezone.utc)

            for job in list(self._jobs.values()):
                if not job.enabled or not job.next_run_date:
                    continue

                next_run = datetime.fromisoformat(job.next_run_date.replace("Z", "+00:00"))
                if next_run <= now:
                    # 执行任务
                    try:
                        if self._on_job:
                            await self._on_job(job)
                        job.run_count += 1
                        job.last_run_date = now.isoformat()
                        logger.info(t("cron.execute_success", name=job.name))
                    except Exception as e:
                        logger.error(t("cron.execute_failed", name=job.name, error=str(e)))

                    # 更新下次执行时间
                    job.next_run_date = self._compute_next_run(job.schedule)

            self._save()
            self._arm_timer()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Cron timer error: {e}")
            # 尝试重新设置定时器
            if self._running:
                self._arm_timer()
