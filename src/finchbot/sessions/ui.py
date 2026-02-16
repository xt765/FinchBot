"""会话列表 UI 组件.

使用 Rich 库提供美观的会话列表界面，支持高亮显示和交互操作。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from finchbot.i18n import t

if TYPE_CHECKING:
    from collections.abc import Sequence

    from finchbot.sessions.metadata import SessionMetadata


class SessionListRenderer:
    """会话列表渲染器.

    负责将会话数据渲染为美观的表格界面。
    """

    # 样式常量
    STYLE_HEADER = "blue bold"
    STYLE_TITLE = "white bold"
    STYLE_MESSAGE_COUNT = "green"
    STYLE_TIME = "dim"

    def __init__(self, console: Console | None = None) -> None:
        """初始化渲染器.

        Args:
            console: Rich 控制台实例，如未提供则创建新实例
        """
        self.console = console or Console()

    def _format_time(self, dt: datetime) -> str:
        """格式化时间显示.

        Args:
            dt: 时间

        Returns:
            本地化后的时间字符串
        """
        now = datetime.now()
        diff = now - dt

        if diff.days == 0:
            if diff.seconds < 60:
                return t("sessions.time.just_now")
            if diff.seconds < 3600:
                minutes = diff.seconds // 60
                return t("sessions.time.minutes_ago", n=minutes)
            hours = diff.seconds // 3600
            return t("sessions.time.hours_ago", n=hours)
        if diff.days == 1:
            return t("sessions.time.yesterday")
        if diff.days < 7:
            return t("sessions.time.days_ago", n=diff.days)
        if diff.days < 30:
            weeks = diff.days // 7
            return t("sessions.time.weeks_ago", n=weeks)
        return dt.strftime("%Y-%m-%d")

    def _truncate_title(self, title: str, max_length: int = 35) -> str:
        """截断标题以适应显示.

        Args:
            title: 原始标题
            max_length: 最大长度

        Returns:
            截断后的标题
        """
        if len(title) <= max_length:
            return title
        return title[: max_length - 3] + "..."

    def render_table(
        self,
        sessions: "Sequence[SessionMetadata]",
    ) -> Table:
        """渲染会话列表表格.

        Args:
            sessions: 会话列表

        Returns:
            Rich Table 对象
        """
        table = Table(
            title=t("sessions.title"),
            box=box.ROUNDED,
            show_header=True,
            header_style=self.STYLE_HEADER,
            border_style="dim",
            padding=(0, 1),
        )

        # 添加列
        table.add_column(t("sessions.columns.title"), min_width=20, ratio=2)
        table.add_column(t("sessions.columns.messages"), width=10, justify="right")
        table.add_column(t("sessions.columns.last_active"), width=15, justify="right")

        for session in sessions:
            # 标题
            title = self._truncate_title(session.title)

            # 消息数
            msg_count = str(session.message_count) if session.message_count > 0 else "-"

            # 时间
            time_str = self._format_time(session.last_active)

            title_text = Text(title, style=self.STYLE_TITLE)
            msg_text = Text(msg_count, style=self.STYLE_MESSAGE_COUNT)
            time_text = Text(time_str, style=self.STYLE_TIME)

            table.add_row(title_text, msg_text, time_text)

        return table

    def render_help(self) -> Panel:
        """渲染帮助信息面板.

        Returns:
            Rich Panel 对象
        """
        help_text = (
            f"{t('sessions.help.navigate')} | "
            f"{t('sessions.help.enter_select')} | "
            f"{t('sessions.help.d_delete')} | "
            f"{t('sessions.help.r_rename')} | "
            f"{t('sessions.help.n_new')} | "
            f"{t('sessions.help.q_quit')}"
        )
        return Panel(
            Text(help_text, style="dim"),
            box=box.SIMPLE,
            padding=(0, 1),
        )

    def render_empty(self) -> Panel:
        """渲染空状态提示.

        Returns:
            Rich Panel 对象
        """
        return Panel(
            Text(t("sessions.no_sessions"), style="yellow", justify="center"),
            box=box.ROUNDED,
            border_style="yellow",
        )

    def render_confirm_delete(self, session_id: str) -> Panel:
        """渲染删除确认提示.

        Args:
            session_id: 要删除的会话 ID

        Returns:
            Rich Panel 对象
        """
        return Panel(
            Text(
                t("sessions.actions.confirm_delete", session_id=session_id),
                style="red bold",
                justify="center",
            ),
            box=box.DOUBLE,
            border_style="red",
            title="⚠️ Confirm",
            title_align="center",
        )


class SessionListUI:
    """会话列表交互式 UI.

    整合渲染和交互逻辑，提供完整的会话管理界面。
    """

    def __init__(self, console: Console | None = None) -> None:
        """初始化 UI.

        Args:
            console: Rich 控制台实例
        """
        self.console = console or Console()
        self.renderer = SessionListRenderer(self.console)

    def display(
        self,
        sessions: "Sequence[SessionMetadata]",
    ) -> None:
        """显示会话列表.

        Args:
            sessions: 会话列表
        """
        if not sessions:
            self.console.print(self.renderer.render_empty())
            return

        # 渲染表格
        table = self.renderer.render_table(sessions)
        self.console.print(table)

        # 渲染帮助信息
        self.console.print(self.renderer.render_help())
