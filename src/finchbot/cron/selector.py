"""交互式定时任务选择器.

使用 readchar 和 Rich 实现键盘导航的定时任务管理界面，
完全模仿 SessionSelector 的设计模式。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import questionary
import readchar
from loguru import logger
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from finchbot.cron.service import CronJob, CronService
from finchbot.i18n import t

if TYPE_CHECKING:
    pass

console = Console()


class CronSelector:
    """交互式定时任务选择器.

    提供键盘导航、高亮显示、快捷键操作的定时任务管理界面，
    完全模仿 SessionSelector 的设计模式。
    """

    def __init__(self, workspace: Path) -> None:
        """初始化选择器.

        Args:
            workspace: 工作目录路径
        """
        self.workspace = workspace
        self.service = CronService(workspace / "data")

    def interactive_manage(self) -> None:
        """交互式任务管理.

        显示任务列表，使用键盘导航选择任务，按不同按键执行操作。
        流程: 显示列表 → 键盘导航选择 → 按键执行操作
        """
        # 加载任务
        self.service._load()

        jobs = list(self.service._jobs.values())

        if not jobs:
            self._handle_empty_jobs()
            return

        selected_idx = 0

        try:
            while True:
                # 清屏并重新渲染
                console.clear()

                # 显示标题
                console.print(f"[bold blue]{t('cron.title')}[/bold blue]")
                console.print()

                # 显示任务列表（带高亮）
                self._render_job_list(jobs, selected_idx)

                # 显示帮助信息（底部固定）
                console.print()
                help_text = (
                    f"[dim cyan]↑↓[/dim cyan] [dim]{t('cron.help.navigate')}[/dim]  "
                    f"[dim cyan]Enter[/dim cyan] [dim]{t('cron.help.detail')}[/dim]  "
                    f"[dim cyan]N[/dim cyan] [dim]{t('cron.help.n_new')}[/dim]  "
                    f"[dim cyan]D[/dim cyan] [dim]{t('cron.help.d_delete')}[/dim]  "
                    f"[dim cyan]E[/dim cyan] [dim]{t('cron.help.e_toggle')}[/dim]  "
                    f"[dim cyan]R[/dim cyan] [dim]{t('cron.help.r_run')}[/dim]  "
                    f"[dim cyan]Q[/dim cyan] [dim]{t('cron.help.q_quit')}[/dim]"
                )
                console.print(help_text)

                # 读取按键
                key = readchar.readkey()

                # 处理按键
                if key == readchar.key.UP:
                    selected_idx = max(0, selected_idx - 1)
                elif key == readchar.key.DOWN:
                    selected_idx = min(len(jobs) - 1, selected_idx + 1)
                elif key == readchar.key.ENTER:
                    # 显示任务详情
                    self._show_job_detail(jobs[selected_idx])
                elif key.lower() == "n":
                    # 新建任务
                    self._handle_new_job()
                    jobs = list(self.service._jobs.values())
                    selected_idx = 0
                elif key.lower() == "d":
                    # 删除任务
                    self._handle_delete_job(jobs[selected_idx])
                    jobs = list(self.service._jobs.values())
                    selected_idx = min(selected_idx, len(jobs) - 1) if jobs else 0
                    if not jobs:
                        return
                elif key.lower() == "e":
                    # 启用/禁用任务
                    self._handle_toggle_job(jobs[selected_idx])
                    jobs = list(self.service._jobs.values())
                elif key.lower() == "r":
                    # 立即执行任务
                    self._handle_run_job(jobs[selected_idx])
                elif key.lower() == "q" or key == readchar.key.CTRL_C:
                    console.print(f"\n[dim]{t('cron.actions.quit')}[/dim]")
                    return

        except KeyboardInterrupt:
            logger.debug("Cron management cancelled by user")
            console.print(f"\n[dim]{t('cron.actions.quit')}[/dim]")

    def _render_job_list(self, jobs: list[CronJob], selected_idx: int) -> None:
        """渲染任务列表（带高亮选中项）.

        Args:
            jobs: 任务列表
            selected_idx: 当前选中索引
        """
        # 创建表格
        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="blue bold",
            border_style="dim",
            padding=(0, 1),
            expand=False,
        )

        # 添加列
        table.add_column("", width=2, justify="center")  # 选中标记列
        table.add_column(t("cron.columns.id"), width=8, justify="center")
        table.add_column(t("cron.columns.name"), min_width=15, max_width=25)
        table.add_column(t("cron.columns.schedule"), width=18)
        table.add_column(t("cron.columns.next_run"), width=14, justify="right")
        table.add_column(t("cron.columns.status"), width=8, justify="center")

        # 添加行
        for idx, job in enumerate(jobs):
            is_selected = idx == selected_idx

            # 选中标记
            cursor = "▶" if is_selected else " "

            # ID（取前 8 位）
            display_id = job.cron_id[:8]

            # 名称（截断）
            name = job.name if len(job.name) <= 25 else job.name[:22] + "..."

            # 调度表达式
            schedule = job.schedule

            # 下次执行时间
            next_run = self._format_next_run(job.next_run_date)

            # 状态
            status = "✅" if job.enabled else "❌"

            # 应用样式
            if is_selected:
                cursor_text = Text(cursor, style="cyan bold")
                id_text = Text(display_id, style="cyan")
                name_text = Text(name, style="cyan bold")
                schedule_text = Text(schedule, style="cyan")
                next_run_text = Text(next_run, style="cyan")
                status_text = Text(status, style="cyan")
            else:
                cursor_text = Text(cursor, style="")
                id_text = Text(display_id, style="dim")
                name_text = Text(name, style="white")
                schedule_text = Text(schedule, style="dim")
                next_run_text = Text(next_run, style="dim")
                status_text = Text(status, style="green" if job.enabled else "red")

            table.add_row(cursor_text, id_text, name_text, schedule_text, next_run_text, status_text)

        console.print(table)

    def _show_job_detail(self, job: CronJob) -> None:
        """显示任务详情.

        Args:
            job: 任务对象
        """
        console.clear()

        # 格式化调度说明
        schedule_desc = self._explain_cron(job.schedule)

        # 格式化时间
        next_run = self._format_datetime(job.next_run_date)
        last_run = self._format_datetime(job.last_run_date)
        created_at = self._format_datetime(job.created_at)

        content = (
            f"[bold]{job.name}[/bold]\n\n"
            f"[dim]{t('cron.detail.id')}:[/] {job.cron_id}\n"
            f"[dim]{t('cron.detail.schedule')}:[/] {job.schedule} ({schedule_desc})\n"
            f"[dim]{t('cron.detail.message')}:[/] {job.message}\n"
            f"[dim]{t('cron.detail.next_run')}:[/] {next_run}\n"
            f"[dim]{t('cron.detail.last_run')}:[/] {last_run or '-'}\n"
            f"[dim]{t('cron.detail.run_count')}:[/] {job.run_count} 次\n"
            f"[dim]{t('cron.detail.status')}:[/] {'✅ ' + t('cron.status.enabled') if job.enabled else '❌ ' + t('cron.status.disabled')}\n"
            f"[dim]{t('cron.detail.created_at')}:[/] {created_at}"
        )

        console.print(
            Panel(
                content,
                title=t("cron.detail.title"),
                box=box.ROUNDED,
            )
        )
        console.print(f"\n[dim]{t('cron.help.any_key_back')}[/dim]")
        readchar.readkey()

    def _handle_empty_jobs(self) -> None:
        """处理无任务情况."""
        console.print(
            Panel(
                Text(t("cron.no_jobs"), style="yellow", justify="center"),
                box=box.ROUNDED,
                border_style="yellow",
            )
        )

        create_new = questionary.confirm(
            t("cron.actions.create_first") + "?",
            default=True,
        ).unsafe_ask()

        if create_new:
            self._handle_new_job()

    def _handle_new_job(self) -> None:
        """新建任务."""
        try:
            # 输入任务名称
            name = questionary.text(
                t("cron.input.name"),
                default="",
            ).unsafe_ask()
            if not name or not name.strip():
                console.print("[dim]已取消[/dim]")
                return
            name = name.strip()

            # 输入时间表达式
            schedule = questionary.text(
                t("cron.input.schedule"),
                default="0 9 * * *",
            ).unsafe_ask()
            if not schedule or not schedule.strip():
                console.print("[dim]已取消[/dim]")
                return
            schedule = schedule.strip()

            # 输入任务内容
            message = questionary.text(
                t("cron.input.message"),
                default="",
            ).unsafe_ask()
            if not message or not message.strip():
                console.print("[dim]已取消[/dim]")
                return
            message = message.strip()

            # 创建任务
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                # 已有事件循环，直接操作
                job = self.service._jobs
                import uuid

                from croniter import croniter

                new_job = CronJob(
                    cron_id=str(uuid.uuid4())[:8],
                    name=name,
                    schedule=schedule,
                    message=message,
                )
                cron = croniter(schedule, datetime.now(timezone.utc))
                new_job.next_run_date = cron.get_next(datetime).isoformat()
                self.service._jobs[new_job.cron_id] = new_job
                self.service._save()
                console.print(f"[green]{t('cron.actions.create_success', name=name)}[/green]")
            except RuntimeError:
                asyncio.run(self.service.create(name, schedule, message))
                console.print(f"[green]{t('cron.actions.create_success', name=name)}[/green]")

        except Exception as e:
            console.print(f"[red]{t('cron.actions.create_failed', error=str(e))}[/red]")

    def _handle_delete_job(self, job: CronJob) -> None:
        """删除任务.

        Args:
            job: 要删除的任务
        """
        confirm = questionary.confirm(
            t("cron.actions.confirm_delete", name=job.name),
            default=False,
        ).unsafe_ask()

        if confirm:
            del self.service._jobs[job.cron_id]
            self.service._save()
            console.print(f"[green]{t('cron.actions.delete_success', name=job.name)}[/green]")

    def _handle_toggle_job(self, job: CronJob) -> None:
        """启用/禁用任务.

        Args:
            job: 要切换的任务
        """
        new_enabled = not job.enabled
        job.enabled = new_enabled

        if new_enabled:
            from croniter import croniter

            cron = croniter(job.schedule, datetime.now(timezone.utc))
            job.next_run_date = cron.get_next(datetime).isoformat()

        self.service._save()

        status = t("cron.status.enabled") if new_enabled else t("cron.status.disabled")
        console.print(f"[green]{t('cron.actions.toggle_success', name=job.name, status=status)}[/green]")

    def _handle_run_job(self, job: CronJob) -> None:
        """立即执行任务.

        Args:
            job: 要执行的任务
        """
        console.print(f"[cyan]{t('cron.actions.running', name=job.name)}...[/cyan]")

        # 更新执行信息
        job.run_count += 1
        job.last_run_date = datetime.now(timezone.utc).isoformat()

        from croniter import croniter

        cron = croniter(job.schedule, datetime.now(timezone.utc))
        job.next_run_date = cron.get_next(datetime).isoformat()

        self.service._save()
        console.print(f"[green]{t('cron.actions.run_success', name=job.name)}[/green]")

    def _format_next_run(self, next_run_date: str | None) -> str:
        """格式化下次执行时间.

        Args:
            next_run_date: ISO 格式的时间字符串

        Returns:
            格式化后的时间字符串
        """
        if not next_run_date:
            return "-"

        try:
            dt = datetime.fromisoformat(next_run_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = dt - now

            if diff.total_seconds() < 0:
                return t("cron.format.overdue")
            elif diff.total_seconds() < 60:
                return t("cron.format.in_seconds", n=int(diff.total_seconds()))
            elif diff.total_seconds() < 3600:
                return t("cron.format.in_minutes", n=int(diff.total_seconds() / 60))
            elif diff.total_seconds() < 86400:
                return t("cron.format.in_hours", n=int(diff.total_seconds() / 3600))
            else:
                return dt.strftime("%m-%d %H:%M")
        except Exception:
            return "-"

    def _format_datetime(self, dt_str: str | None) -> str:
        """格式化日期时间.

        Args:
            dt_str: ISO 格式的时间字符串

        Returns:
            格式化后的时间字符串
        """
        if not dt_str:
            return "-"
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "-"

    def _explain_cron(self, schedule: str) -> str:
        """解释 cron 表达式.

        Args:
            schedule: cron 表达式

        Returns:
            人类可读的说明
        """
        try:
            parts = schedule.split()
            if len(parts) != 5:
                return schedule

            minute, hour, day, month, weekday = parts

            # 常见模式
            if minute == "0" and hour != "*" and day == "*" and month == "*" and weekday == "*":
                return f"每天 {hour}:00"

            if minute.startswith("*/") and hour == "*":
                interval = minute[2:]
                return f"每 {interval} 分钟"

            if minute == "0" and hour.startswith("*/"):
                interval = hour[2:]
                return f"每 {interval} 小时"

            if weekday != "*" and weekday not in ("*", "0-6", "1-5"):
                weekday_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
                try:
                    wd = int(weekday)
                    return f"每{weekday_names[wd]} {hour}:{minute.zfill(2)}"
                except ValueError:
                    pass

            return schedule

        except Exception:
            return schedule


def run_cron_selector(workspace: Path) -> None:
    """运行定时任务交互式选择器.

    Args:
        workspace: 工作目录
    """
    selector = CronSelector(workspace)
    selector.interactive_manage()
