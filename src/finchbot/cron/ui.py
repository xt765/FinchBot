"""定时任务交互式 UI.

使用键盘导航和 Rich 渲染提供美观的任务管理界面。
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import questionary
import readchar
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


class CronTaskUI:
    """定时任务交互式 UI.

    提供键盘导航、高亮显示、快捷键操作的任务管理界面。
    """

    def __init__(self, cron_service: CronService, workspace: Path) -> None:
        """初始化 UI.

        Args:
            cron_service: 定时任务服务
            workspace: 工作目录
        """
        self.cron_service = cron_service
        self.workspace = workspace

    def interactive_manage(self) -> None:
        """交互式任务管理.

        显示任务列表，使用键盘导航选择任务，按不同按键执行操作。
        """
        while True:
            jobs = self._get_jobs()

            if not jobs:
                self._handle_empty_jobs()
                return

            selected_idx = 0

            try:
                while True:
                    console.clear()
                    self._render_job_list(jobs, selected_idx)
                    self._render_help()

                    key = readchar.readkey()

                    if key == readchar.key.UP:
                        selected_idx = max(0, selected_idx - 1)
                    elif key == readchar.key.DOWN:
                        selected_idx = min(len(jobs) - 1, selected_idx + 1)
                    elif key == readchar.key.ENTER:
                        self._show_job_detail(jobs[selected_idx])
                    elif key.lower() == "n":
                        self._handle_new_job()
                        jobs = self._get_jobs()
                    elif key.lower() == "d":
                        self._handle_delete_job(jobs[selected_idx])
                        jobs = self._get_jobs()
                        selected_idx = min(selected_idx, len(jobs) - 1) if jobs else 0
                        if not jobs:
                            break
                    elif key.lower() == "e":
                        self._handle_toggle_job(jobs[selected_idx])
                        jobs = self._get_jobs()
                    elif key.lower() == "r":
                        self._handle_run_job(jobs[selected_idx])
                    elif key.lower() == "q" or key == readchar.key.CTRL_C:
                        console.print(f"\n[dim]{t('cron.actions.quit')}[/dim]")
                        return

            except KeyboardInterrupt:
                console.print(f"\n[dim]{t('cron.actions.quit')}[/dim]")
                return

    def _get_jobs(self) -> list[CronJob]:
        """获取任务列表."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.cron_service.list(include_disabled=True))

        # 如果已有事件循环，使用 run_until_complete
        with contextlib.suppress(Exception):
            return list(self.cron_service._jobs.values())
        return []

    def _render_job_list(self, jobs: list[CronJob], selected_idx: int) -> None:
        """渲染任务列表.

        Args:
            jobs: 任务列表
            selected_idx: 选中索引
        """
        console.print(f"[bold blue]{t('cron.title')}[/bold blue]\n")

        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="blue bold",
            border_style="dim",
            padding=(0, 1),
        )

        table.add_column("", width=2)
        table.add_column(t("cron.columns.id"), width=8)
        table.add_column(t("cron.columns.name"), min_width=15, max_width=25)
        table.add_column(t("cron.columns.schedule"), width=18)
        table.add_column(t("cron.columns.next_run"), width=16)
        table.add_column(t("cron.columns.status"), width=10)

        for idx, job in enumerate(jobs):
            is_selected = idx == selected_idx
            cursor = "▶" if is_selected else " "

            next_run_str = self._format_next_run(job.next_run_date)
            status_str = t("cron.status.enabled") if job.enabled else t("cron.status.disabled")

            style = "cyan bold" if is_selected else ("dim" if not job.enabled else None)

            table.add_row(
                Text(cursor, style=style),
                Text(job.cron_id, style=style),
                Text(job.name[:25], style=style),
                Text(job.schedule, style=style),
                Text(next_run_str, style=style),
                Text(status_str, style="green" if job.enabled else "red"),
            )

        console.print(table)

    def _render_help(self) -> None:
        """渲染帮助信息."""
        help_text = (
            f"[dim cyan]↑↓[/dim cyan] [dim]{t('cron.help.navigate')}[/dim]  "
            f"[dim cyan]Enter[/dim cyan] [dim]{t('cron.help.detail')}[/dim]  "
            f"[dim cyan]N[/dim cyan] [dim]{t('cron.help.n_new')}[/dim]  "
            f"[dim cyan]D[/dim cyan] [dim]{t('cron.help.d_delete')}[/dim]  "
            f"[dim cyan]E[/dim cyan] [dim]{t('cron.help.e_toggle')}[/dim]  "
            f"[dim cyan]R[/dim cyan] [dim]{t('cron.help.r_run')}[/dim]  "
            f"[dim cyan]Q[/dim cyan] [dim]{t('cron.help.q_quit')}[/dim]"
        )
        console.print(f"\n{help_text}")

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
        """创建新任务."""
        import asyncio

        try:
            name = questionary.text(t("cron.input.name")).unsafe_ask()
            if not name:
                return

            schedule = questionary.text(
                t("cron.input.schedule"),
                default="0 9 * * *",
            ).unsafe_ask()
            if not schedule:
                return

            message = questionary.text(t("cron.input.message")).unsafe_ask()
            if not message:
                return

            # 创建任务
            try:
                loop = asyncio.get_running_loop()
                # 如果已有事件循环，直接操作
                import uuid

                from croniter import croniter

                job = CronJob(
                    cron_id=str(uuid.uuid4())[:8],
                    name=name,
                    schedule=schedule,
                    message=message,
                )
                now_local = datetime.now().astimezone()
                cron = croniter(schedule, now_local)
                next_dt_local = cron.get_next(datetime)
                job.next_run_date = next_dt_local.astimezone(timezone.utc).isoformat()
                self.cron_service._jobs[job.cron_id] = job
                self.cron_service._save()
            except RuntimeError:
                asyncio.run(self.cron_service.create(name, schedule, message))

            console.print(f"[green]{t('cron.actions.create_success', name=name)}[/green]")

        except Exception as e:
            console.print(f"[red]{t('cron.actions.create_failed', error=str(e))}[/red]")

    def _handle_delete_job(self, job: CronJob) -> None:
        """删除任务.

        Args:
            job: 要删除的任务
        """
        import asyncio

        confirm = questionary.confirm(
            t("cron.actions.confirm_delete", name=job.name),
            default=False,
        ).unsafe_ask()

        if confirm:
            try:
                loop = asyncio.get_running_loop()
                del self.cron_service._jobs[job.cron_id]
                self.cron_service._save()
            except RuntimeError:
                asyncio.run(self.cron_service.delete(job.cron_id))
            console.print(f"[green]{t('cron.actions.delete_success', name=job.name)}[/green]")

    def _handle_toggle_job(self, job: CronJob) -> None:
        """启用/禁用任务.

        Args:
            job: 要切换的任务
        """
        import asyncio

        new_enabled = not job.enabled
        try:
            loop = asyncio.get_running_loop()
            job.enabled = new_enabled
            if new_enabled:
                from croniter import croniter

                now_local = datetime.now().astimezone()
                cron = croniter(job.schedule, now_local)
                next_dt_local = cron.get_next(datetime)
                job.next_run_date = next_dt_local.astimezone(timezone.utc).isoformat()
            self.cron_service._save()
        except RuntimeError:
            asyncio.run(self.cron_service.toggle(job.cron_id, new_enabled))

        status = t("cron.status.enabled") if new_enabled else t("cron.status.disabled")
        console.print(
            f"[green]{t('cron.actions.toggle_success', name=job.name, status=status)}[/green]"
        )

    def _handle_run_job(self, job: CronJob) -> None:
        """立即执行任务.

        Args:
            job: 要执行的任务
        """
        import asyncio

        console.print(f"[cyan]{t('cron.actions.running', name=job.name)}...[/cyan]")

        try:
            loop = asyncio.get_running_loop()
            # 直接执行
            job.run_count += 1
            job.last_run_date = datetime.now(timezone.utc).isoformat()
            from croniter import croniter

            now_local = datetime.now().astimezone()
            cron = croniter(job.schedule, now_local)
            next_dt_local = cron.get_next(datetime)
            job.next_run_date = next_dt_local.astimezone(timezone.utc).isoformat()
            self.cron_service._save()
            console.print(f"[green]{t('cron.actions.run_success', name=job.name)}[/green]")
        except RuntimeError:
            result = asyncio.run(self.cron_service.run_now(job.cron_id))
            if result and not result.startswith("Error"):
                console.print(f"[green]{t('cron.actions.run_success', name=job.name)}[/green]")
            else:
                console.print(
                    f"[red]{t('cron.actions.run_failed', error=result or 'Unknown')}[/red]"
                )
        except Exception as e:
            console.print(f"[red]{t('cron.actions.run_failed', error=str(e))}[/red]")

    def _show_job_detail(self, job: CronJob) -> None:
        """显示任务详情.

        Args:
            job: 任务对象
        """
        console.clear()
        content = (
            f"[bold]{job.name}[/bold]\n\n"
            f"[dim]{t('cron.detail.id')}:[/] {job.cron_id}\n"
            f"[dim]{t('cron.detail.schedule')}:[/] {job.schedule}\n"
            f"[dim]{t('cron.detail.message')}:[/] {job.message}\n"
            f"[dim]{t('cron.detail.next_run')}:[/] {self._format_next_run(job.next_run_date)}\n"
            f"[dim]{t('cron.detail.run_count')}:[/] {job.run_count}\n"
            f"[dim]{t('cron.detail.status')}:[/] {'✅' if job.enabled else '❌'}\n"
            f"[dim]{t('cron.detail.created_at')}:[/] {self._format_datetime(job.created_at)}"
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


def run_cron_ui(workspace: Path) -> None:
    """运行定时任务交互式 UI.

    Args:
        workspace: 工作目录
    """
    import asyncio

    cron_service = CronService(workspace / "data")

    # 尝试加载已有数据
    try:
        loop = asyncio.get_running_loop()
        cron_service._load()
    except RuntimeError:
        asyncio.run(cron_service.start())

    ui = CronTaskUI(cron_service, workspace)
    ui.interactive_manage()
