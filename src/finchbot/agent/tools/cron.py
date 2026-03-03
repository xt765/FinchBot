"""定时任务工具集.

提供创建、列出、删除、切换定时任务的工具。
支持三种调度模式：at（一次性）、every（间隔）、cron（表达式）。
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool
from loguru import logger

from finchbot.cron.service import CronService
from finchbot.cron.types import CronSchedule, now_ms
from finchbot.i18n import t

_cron_service: CronService | None = None


def get_cron_service(workspace: Path | None = None) -> CronService:
    """获取 CronService 单例.

    Args:
        workspace: 工作目录（首次调用时需要）

    Returns:
        CronService 实例
    """
    global _cron_service
    if _cron_service is None:
        if workspace is None:
            workspace = Path.cwd()
        _cron_service = CronService(workspace / "data")
    return _cron_service


def set_cron_service(service: CronService) -> None:
    """设置全局 CronService.

    Args:
        service: CronService 实例
    """
    global _cron_service
    _cron_service = service


def _format_next_run(next_run_at_ms: int | None) -> str:
    """格式化下次执行时间.

    Args:
        next_run_at_ms: 下次执行时间戳（毫秒）

    Returns:
        格式化后的时间字符串
    """
    if not next_run_at_ms:
        return "-"

    from datetime import datetime

    current_ms = now_ms()
    diff_ms = next_run_at_ms - current_ms

    if diff_ms < 0:
        return t("cron.format.overdue")
    elif diff_ms < 60000:
        return t("cron.format.in_seconds", n=int(diff_ms / 1000))
    elif diff_ms < 3600000:
        return t("cron.format.in_minutes", n=int(diff_ms / 60000))
    elif diff_ms < 86400000:
        return t("cron.format.in_hours", n=int(diff_ms / 3600000))
    else:
        dt = datetime.fromtimestamp(next_run_at_ms / 1000)
        return dt.strftime("%m-%d %H:%M")


@tool
def create_cron(
    name: str,
    message: str,
    every_seconds: int | None = None,
    cron_expr: str | None = None,
    tz: str | None = None,
    at: str | None = None,
) -> str:
    """创建定时任务.

    支持三种调度模式（三选一）：

    1. every_seconds: 间隔任务，每 N 秒执行一次
       - 适用场景：定期检查、周期性同步
       - 示例：every_seconds=3600（每小时）

    2. cron_expr: cron 表达式，精确时间调度
       - 适用场景：固定时间点执行
       - 示例：cron_expr="0 9 * * *"（每天 9:00）
       - 可选 tz 参数指定时区，如 "Asia/Shanghai"

    3. at: 一次性任务，指定时间执行后自动删除
       - 适用场景：提醒、一次性操作
       - 示例：at="2025-01-15T10:30:00"

    定时任务执行时，Agent 会收到消息通知。

    Args:
        name: 任务名称
        message: 任务内容/描述
        every_seconds: 间隔秒数（用于间隔任务）
        cron_expr: cron 表达式（用于定时任务）
        tz: IANA 时区名称，如 "Asia/Shanghai"（仅用于 cron_expr）
        at: ISO 格式时间字符串（用于一次性任务）

    Returns:
        创建结果信息
    """
    service = get_cron_service()

    try:
        delete_after_run = False

        if every_seconds:
            schedule = CronSchedule(kind="every", every_ms=every_seconds * 1000)
        elif cron_expr:
            schedule = CronSchedule(kind="cron", expr=cron_expr, tz=tz)
        elif at:
            from datetime import datetime

            dt = datetime.fromisoformat(at)
            at_ms = int(dt.timestamp() * 1000)
            schedule = CronSchedule(kind="at", at_ms=at_ms)
            delete_after_run = True
        else:
            return "Error: 必须指定 every_seconds、cron_expr 或 at 其中之一"

        job = service.add_job(
            name=name,
            schedule=schedule,
            message=message,
            delete_after_run=delete_after_run,
        )

        next_run = _format_next_run(job.state.next_run_at_ms)
        return (
            t("cron.job_created", id=job.id, schedule=schedule.expr or schedule.kind)
            + f" (下次执行: {next_run})"
        )

    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Failed to create cron job: {e}")
        return f"Error: {e}"


@tool
def list_crons(include_disabled: bool = True) -> str:
    """列出所有定时任务.

    返回所有已创建的定时任务列表，包含状态和下次执行时间。

    Args:
        include_disabled: 是否包含已禁用的任务

    Returns:
        任务列表信息
    """
    service = get_cron_service()
    jobs = service.list_jobs(include_disabled=include_disabled)

    if not jobs:
        return t("cron.no_jobs")

    lines = [t("cron.title")]
    for job in jobs:
        status = "✅" if job.enabled else "❌"
        schedule_info = job.schedule.expr if job.schedule.kind == "cron" else job.schedule.kind
        next_run = _format_next_run(job.state.next_run_at_ms)
        last_status = f" [{job.state.last_status}]" if job.state.last_status else ""
        lines.append(
            f"  {status} [{job.id}] {job.name}: {schedule_info} (下次: {next_run}){last_status}"
        )

    return "\n".join(lines)


@tool
def delete_cron(cron_id: str) -> str:
    """删除定时任务.

    删除指定的定时任务。

    Args:
        cron_id: 任务 ID

    Returns:
        删除结果信息
    """
    service = get_cron_service()
    success = service.remove_job(cron_id)

    if success:
        return t("cron.job_deleted", id=cron_id)
    else:
        return t("cron.job_not_found", id=cron_id)


@tool
def toggle_cron(cron_id: str, enabled: bool) -> str:
    """启用或禁用定时任务.

    切换定时任务的启用状态。

    Args:
        cron_id: 任务 ID
        enabled: 是否启用（true/false）

    Returns:
        操作结果信息
    """
    service = get_cron_service()
    job = service.enable_job(cron_id, enabled)

    if job:
        status = t("cron.status.enabled") if enabled else t("cron.status.disabled")
        return t("cron.actions.toggle_success", name=job.name, status=status)
    else:
        return t("cron.job_not_found", id=cron_id)


@tool
async def run_cron_now(cron_id: str) -> str:
    """立即执行定时任务.

    立即执行指定的定时任务，不等待下次计划时间。

    Args:
        cron_id: 任务 ID

    Returns:
        执行结果信息
    """
    service = get_cron_service()
    success = await service.run_job(cron_id, force=True)

    if success:
        job = service.get_job(cron_id)
        if job and job.state.last_status == "ok":
            return t("cron.execute_success", name=job.name)
        elif job and job.state.last_error:
            return t("cron.execute_failed", name=job.name, error=job.state.last_error)
        return t("cron.execute_success", name=cron_id)
    else:
        return t("cron.job_not_found", id=cron_id)


@tool
def get_cron_status(cron_id: str) -> str:
    """获取定时任务详细状态.

    返回指定任务的详细信息，包括执行历史。

    Args:
        cron_id: 任务 ID

    Returns:
        任务状态信息
    """
    service = get_cron_service()
    job = service.get_job(cron_id)

    if not job:
        return t("cron.job_not_found", id=cron_id)

    from datetime import datetime

    def format_time(ms: int | None) -> str:
        if not ms:
            return "-"
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"**{job.name}** (ID: {job.id})",
        f"状态: {'✅ 启用' if job.enabled else '❌ 禁用'}",
        f"调度类型: {job.schedule.kind}",
    ]

    if job.schedule.kind == "cron":
        lines.append(f"Cron 表达式: {job.schedule.expr}")
        if job.schedule.tz:
            lines.append(f"时区: {job.schedule.tz}")
    elif job.schedule.kind == "every":
        lines.append(f"间隔: {job.schedule.every_ms // 1000} 秒")
    elif job.schedule.kind == "at":
        lines.append(f"执行时间: {format_time(job.schedule.at_ms)}")

    lines.extend(
        [
            f"消息: {job.payload.message}",
            f"下次执行: {format_time(job.state.next_run_at_ms)}",
            f"上次执行: {format_time(job.state.last_run_at_ms)}",
            f"上次状态: {job.state.last_status or '-'}",
        ]
    )

    if job.state.last_error:
        lines.append(f"错误信息: {job.state.last_error}")

    return "\n".join(lines)


CRON_TOOLS = [
    create_cron,
    list_crons,
    delete_cron,
    toggle_cron,
    run_cron_now,
    get_cron_status,
]
