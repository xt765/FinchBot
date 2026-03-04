"""后台任务工具集.

使用 LangGraph 官方推荐的 Three-tool pattern 实现异步后台任务。
集成 SubagentManager 实现真正的子代理执行。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from langchain_core.tools import tool
from loguru import logger
from pydantic import BaseModel, Field

from finchbot.i18n import t

if TYPE_CHECKING:
    from finchbot.agent.subagent import SubagentManager


class JobStatus(BaseModel):
    """任务状态."""

    job_id: str
    status: str
    result: str | None = None
    error: str | None = None
    label: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    task_id: str | None = None


class JobManager:
    """任务管理器（单例模式）.

    管理所有后台任务的生命周期。

    Attributes:
        _instance: 单例实例
        _jobs: 任务状态映射
        _subagent_manager: 子代理管理器
    """

    _instance: JobManager | None = None
    _jobs: dict[str, JobStatus]
    _subagent_manager: SubagentManager | None = None

    def __new__(cls) -> JobManager:
        """创建或返回单例实例."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._jobs = {}
            cls._instance._subagent_manager = None
        return cls._instance

    def set_subagent_manager(self, manager: SubagentManager) -> None:
        """设置子代理管理器.

        Args:
            manager: SubagentManager 实例
        """
        self._subagent_manager = manager

    def get_subagent_manager(self) -> SubagentManager | None:
        """获取子代理管理器.

        Returns:
            SubagentManager 实例
        """
        return self._subagent_manager

    def create_job(self, label: str | None = None) -> str:
        """创建新任务 ID.

        Args:
            label: 任务标签

        Returns:
            新任务 ID
        """
        job_id = str(uuid.uuid4())[:8]
        self._jobs[job_id] = JobStatus(job_id=job_id, status="pending", label=label)
        return job_id

    def update_status(
        self,
        job_id: str,
        status: str,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        """更新任务状态.

        Args:
            job_id: 任务 ID
            status: 新状态
            result: 任务结果（可选）
            error: 错误信息（可选）
        """
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = status
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            if status == "running" and job.started_at is None:
                job.started_at = datetime.now(UTC)
            if status in ("completed", "failed", "cancelled"):
                job.completed_at = datetime.now(UTC)

    def get_status(self, job_id: str) -> JobStatus | None:
        """获取任务状态.

        Args:
            job_id: 任务 ID

        Returns:
            任务状态，不存在则返回 None
        """
        return self._jobs.get(job_id)

    def list_jobs(self, include_completed: bool = True) -> list[JobStatus]:
        """列出所有任务.

        Args:
            include_completed: 是否包含已完成的任务

        Returns:
            任务列表
        """
        jobs = list(self._jobs.values())
        if not include_completed:
            jobs = [j for j in jobs if j.status not in ("completed", "failed", "cancelled")]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """清理旧任务.

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            清理的任务数量
        """
        now = datetime.now(UTC)
        to_remove = []
        for job_id, job in self._jobs.items():
            if job.completed_at:
                age = (now - job.completed_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(job_id)

        for job_id in to_remove:
            self._jobs.pop(job_id, None)

        return len(to_remove)

    def clear_all(self) -> int:
        """清理所有任务.

        Returns:
            清理的任务数量
        """
        count = len(self._jobs)
        self._jobs.clear()
        return count

    def associate_job(self, job_id: str, task_id: str) -> None:
        """关联任务 ID 和子代理 ID.

        Args:
            job_id: 任务 ID
            task_id: 子代理 ID
        """
        if job_id in self._jobs:
            self._jobs[job_id].task_id = task_id

    def get_job_by_task(self, task_id: str) -> JobStatus | None:
        """通过子代理 ID 获取任务状态.

        Args:
            task_id: 子代理 ID

        Returns:
            任务状态，不存在则返回 None
        """
        for job in self._jobs.values():
            if job.task_id == task_id:
                return job
        return None


def get_job_manager() -> JobManager:
    """获取任务管理器单例.

    Returns:
        JobManager 实例
    """
    return JobManager()


async def _execute_background_task(
    job_id: str,
    task_description: str,
    label: str | None = None,
    session_key: str = "cli:default",
) -> str:
    """执行后台任务的核心逻辑.

    Args:
        job_id: 任务 ID
        task_description: 任务描述
        label: 任务标签
        session_key: 会话标识

    Returns:
        执行结果
    """
    manager = get_job_manager()
    manager.update_status(job_id, "running")

    subagent_manager = manager.get_subagent_manager()

    try:
        if subagent_manager:
            task_id = await subagent_manager.spawn_and_wait(
                task=task_description,
                label=label,
                session_key=session_key,
            )
            manager.associate_job(job_id, task_id)

            result = await subagent_manager.wait_for_result(task_id, timeout=300)
            if result:
                manager.update_status(job_id, "completed", result=result)
                logger.info(f"Background task {job_id} completed")
                return result
            else:
                manager.update_status(job_id, "completed", result="Task started in background")
                return f"Task {job_id} started in background. Use check_task_status to monitor."
        else:
            logger.warning(f"No SubagentManager available for task {job_id}")
            await asyncio.sleep(1)
            result = f"Task completed (simulated): {task_description[:100]}"
            manager.update_status(job_id, "completed", result=result)
            logger.info(f"Background task {job_id} completed (no subagent manager)")
            return result

    except asyncio.CancelledError:
        manager.update_status(job_id, "cancelled")
        logger.info(f"Background task {job_id} cancelled")
        raise

    except Exception as e:
        manager.update_status(job_id, "failed", error=str(e))
        logger.error(f"Background task {job_id} failed: {e}")
        raise


@tool
async def start_background_task(
    task_description: str,
    label: str | None = None,
) -> str:
    """启动后台任务.

    创建一个独立子代理在后台执行任务。子代理拥有完整的工具集，
    最多执行 15 次迭代。任务异步执行，你可以继续当前对话。

    使用场景：
    - 长时间运行的分析任务
    - 需要多步骤执行的复杂操作
    - 不需要立即结果的任务

    使用 check_task_status 检查状态，get_task_result 获取结果。

    Args:
        task_description: 任务描述，详细说明要执行的任务
        label: 可选的任务标签（用于显示和识别）

    Returns:
        任务启动信息，包含任务 ID
    """
    manager = get_job_manager()
    job_id = manager.create_job(label)

    try:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        writer({"job_id": job_id, "status": "started", "type": "background_task"})
    except Exception:
        pass

    asyncio.create_task(
        _execute_background_task(job_id, task_description, label),
    )

    logger.info(f"Background task started: {job_id}")
    return t("background.task_started", job_id=job_id)


@tool
def check_task_status(job_id: str) -> str:
    """检查任务状态.

    返回指定任务的当前状态。状态包括：
    - pending: 等待执行
    - running: 正在执行
    - completed: 已完成
    - failed: 执行失败
    - cancelled: 已取消

    Args:
        job_id: 任务 ID

    Returns:
        任务状态信息
    """
    manager = get_job_manager()
    status = manager.get_status(job_id)

    if not status:
        return t("background.job_not_found", job_id=job_id)

    if status.error:
        return t(
            "background.status_with_error",
            job_id=job_id,
            status=status.status,
            error=status.error,
        )
    elif status.result:
        truncated = status.result[:200] + ("..." if len(status.result) > 200 else "")
        return t(
            "background.status_with_result",
            job_id=job_id,
            status=status.status,
            result=truncated,
        )
    else:
        return t("background.status_report", job_id=job_id, status=status.status)


@tool
def get_task_result(job_id: str) -> str:
    """获取任务结果.

    获取已完成任务的详细结果。仅当任务状态为 completed 时可用。

    Args:
        job_id: 任务 ID

    Returns:
        任务结果
    """
    manager = get_job_manager()
    status = manager.get_status(job_id)

    if not status:
        return t("background.job_not_found", job_id=job_id)

    if status.status != "completed":
        return t("background.job_not_completed", job_id=job_id, status=status.status)

    return status.result or t("background.no_result")


@tool
def cancel_task(job_id: str) -> str:
    """取消后台任务.

    取消正在运行的后台任务。只能取消状态为 pending 或 running 的任务。

    Args:
        job_id: 任务 ID

    Returns:
        取消结果信息
    """
    manager = get_job_manager()
    status = manager.get_status(job_id)

    if not status:
        return t("background.job_not_found", job_id=job_id)

    if status.status in ("completed", "failed", "cancelled"):
        return t("background.job_not_completed", job_id=job_id, status=status.status)

    subagent_manager = manager.get_subagent_manager()
    if subagent_manager and subagent_manager.cancel_task(job_id):
        manager.update_status(job_id, "cancelled")
        return t("background.cancel_success", job_id=job_id)

    manager.update_status(job_id, "cancelled")
    return t("background.cancel_success", job_id=job_id)


@tool
def list_background_tasks(include_completed: bool = False) -> str:
    """列出后台任务.

    返回所有后台任务的状态列表。

    Args:
        include_completed: 是否包含已完成的任务

    Returns:
        任务列表信息
    """
    manager = get_job_manager()
    jobs = manager.list_jobs(include_completed=include_completed)

    if not jobs:
        return "No background tasks."

    lines = ["Background Tasks:"]
    for job in jobs:
        status_icon = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫",
        }.get(job.status, "❓")
        label = job.label or job.job_id
        lines.append(f"  {status_icon} [{job.job_id}] {label}: {job.status}")

    return "\n".join(lines)


BACKGROUND_TOOLS = [
    start_background_task,
    check_task_status,
    get_task_result,
    cancel_task,
    list_background_tasks,
]
