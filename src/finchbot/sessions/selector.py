"""交互式会话选择器.

使用 readchar 和 Rich 实现键盘导航的会话选择界面，
支持选择、删除、重命名等操作。
"""

from pathlib import Path
from typing import TYPE_CHECKING

import questionary
import readchar
from loguru import logger
from rich.console import Console

from finchbot.i18n import t
from finchbot.sessions.metadata import SessionMetadata, SessionMetadataStore
from finchbot.sessions.ui import SessionListRenderer

if TYPE_CHECKING:
    from collections.abc import Sequence


console = Console()


class SessionSelector:
    """交互式会话选择器.

    提供键盘导航、高亮显示、Enter 确认的会话选择界面，
    支持在选择界面直接执行删除和重命名操作。
    """

    def __init__(self, workspace: Path) -> None:
        """初始化选择器.

        Args:
            workspace: 工作目录路径
        """
        self.workspace = workspace
        self.store = SessionMetadataStore(workspace)
        self.renderer = SessionListRenderer(console)

    def _format_session_choice(self, session: SessionMetadata) -> str:
        """格式化会话选项显示.

        Args:
            session: 会话元数据

        Returns:
            格式化的选项字符串
        """
        time_str = self.renderer._format_time(session.last_active)
        msg_count = f"{session.message_count}条消息" if session.message_count > 0 else "新会话"

        # 限制标题长度
        title = session.title
        if len(title) > 30:
            title = title[:27] + "..."

        return f"{title} ({msg_count}) - {time_str}"

    def interactive_manage(self) -> None:
        """交互式会话管理.

        显示会话列表，使用键盘导航选择会话，按不同按键执行操作。
        流程: 显示列表 → 键盘导航选择 → 按键执行操作
        """
        sessions = self.store.get_all_sessions()

        if not sessions:
            self._handle_empty_sessions()
            return

        # 使用键盘监听模式
        self._interactive_select_with_keys(sessions)

    def _handle_empty_sessions(self) -> None:
        """处理无会话情况."""
        console.print(t("sessions.no_sessions"))
        create_new = questionary.confirm(
            t("sessions.new_session") + "?",
            default=True,
        ).unsafe_ask()

        if create_new:
            self._handle_new_session()

    def _interactive_select_with_keys(self, sessions: "Sequence[SessionMetadata]") -> None:
        """使用键盘监听进行交互式选择.

        Args:
            sessions: 会话列表
        """
        selected_idx = 0

        try:
            while True:
                # 清屏并重新渲染
                console.clear()

                # 显示标题
                console.print(f"[bold blue]{t('sessions.title')}[/bold blue]")
                console.print()

                # 显示会话列表（带高亮）
                self._render_session_list(sessions, selected_idx)

                # 显示帮助信息（底部固定）
                console.print()
                help_text = (
                    f"[dim cyan]↑↓[/dim cyan] [dim]{t('sessions.help.navigate')}[/dim]  "
                    f"[dim cyan]Enter[/dim cyan] [dim]{t('sessions.help.enter_select')}[/dim]  "
                    f"[dim cyan]D[/dim cyan] [dim]{t('sessions.help.d_delete')}[/dim]  "
                    f"[dim cyan]R[/dim cyan] [dim]{t('sessions.help.r_rename')}[/dim]  "
                    f"[dim cyan]N[/dim cyan] [dim]{t('sessions.help.n_new')}[/dim]  "
                    f"[dim cyan]Q[/dim cyan] [dim]{t('sessions.help.q_quit')}[/dim]"
                )
                console.print(help_text)

                # 读取按键
                key = readchar.readkey()

                # 处理按键
                if key == readchar.key.UP:
                    selected_idx = max(0, selected_idx - 1)
                elif key == readchar.key.DOWN:
                    selected_idx = min(len(sessions) - 1, selected_idx + 1)
                elif key == readchar.key.ENTER:
                    # 执行选中项的默认操作（进入聊天）
                    self._handle_enter_key(sessions[selected_idx].session_id, sessions)
                    # 聊天结束后，重新获取会话列表并继续循环
                    sessions = self.store.get_all_sessions()
                    if not sessions:
                        return
                    selected_idx = min(selected_idx, len(sessions) - 1)
                    # 继续循环，重新显示列表
                elif key.lower() == "d":
                    # 删除选中的会话
                    session_id = sessions[selected_idx].session_id
                    if self._confirm_and_delete(session_id):
                        # 重新排列会话 ID
                        self._rearrange_session_ids()
                        # 刷新会话列表
                        sessions = self.store.get_all_sessions()
                        if not sessions:
                            return
                        selected_idx = min(selected_idx, len(sessions) - 1)
                elif key.lower() == "r":
                    # 重命名选中的会话
                    session_id = sessions[selected_idx].session_id
                    self._rename_session(session_id)
                    # 刷新列表
                    sessions = self.store.get_all_sessions()
                elif key.lower() == "n":
                    # 新建会话
                    self._handle_new_session()
                    # 聊天结束后，重新获取会话列表并继续循环
                    sessions = self.store.get_all_sessions()
                    if not sessions:
                        return
                    selected_idx = 0
                elif key.lower() == "q" or key == readchar.key.CTRL_C:
                    # 退出
                    return

        except KeyboardInterrupt:
            logger.debug("Session management cancelled by user")

    def _render_session_list(
        self,
        sessions: "Sequence[SessionMetadata]",
        selected_idx: int,
    ) -> None:
        """渲染会话列表（带高亮选中项）.

        Args:
            sessions: 会话列表
            items: (value, display) 元组列表
            selected_idx: 当前选中索引
        """
        from rich import box
        from rich.table import Table
        from rich.text import Text

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
        table.add_column(t("sessions.columns.id"), width=6, justify="center")
        table.add_column(t("sessions.columns.title"), min_width=15, max_width=25, ratio=2)
        table.add_column(t("sessions.columns.messages"), width=8, justify="right")
        table.add_column(t("sessions.columns.created"), width=12, justify="right")
        table.add_column(t("sessions.columns.last_active"), width=12, justify="right")

        # 添加行
        for idx, session in enumerate(sessions):
            is_selected = idx == selected_idx

            # 选中标记
            cursor = "▶" if is_selected else " "

            # ID（序号）
            session_id = str(idx + 1)

            # 标题（为空时显示占位符）
            title = session.title if session.title.strip() else t("sessions.empty_title")
            if len(title) > 25:
                title = title[:22] + "..."

            # 消息数
            msg_count = str(session.message_count) if session.message_count > 0 else "-"

            # 创建时间
            created_str = self.renderer._format_time(session.created_at)

            # 最后活跃时间
            time_str = self.renderer._format_time(session.last_active)

            # 应用样式
            if is_selected:
                cursor_text = Text(cursor, style="cyan bold")
                id_text = Text(session_id, style="cyan")
                title_text = Text(title, style="cyan bold")
                msg_text = Text(msg_count, style="cyan")
                created_text = Text(created_str, style="cyan")
                time_text = Text(time_str, style="cyan")
            else:
                cursor_text = Text(cursor, style="")
                id_text = Text(session_id, style="dim")
                title_text = Text(title, style="white")
                msg_text = Text(msg_count, style="green")
                created_text = Text(created_str, style="dim")
                time_text = Text(time_str, style="dim")

            table.add_row(cursor_text, id_text, title_text, msg_text, created_text, time_text)

        console.print(table)

    def _handle_enter_key(self, session_id: str, sessions: "Sequence[SessionMetadata]") -> None:
        """处理 Enter 键.

        Args:
            session_id: 选中的会话 ID
            sessions: 会话列表（用于新建会话后刷新）
        """
        from finchbot.cli import _run_chat_session

        config_obj = self._load_config()
        ws_path = Path(config_obj.agents.defaults.workspace).expanduser()
        console.print(f"[green]✓ {t('sessions.actions.enter_chat')}: {session_id}[/green]\n")
        _run_chat_session(session_id, None, str(ws_path))

    def _handle_new_session(self) -> None:
        """处理新建会话.

        创建新会话并进入聊天，聊天结束后返回。
        """
        from finchbot.cli import _run_chat_session

        try:
            new_name = questionary.text(
                t("sessions.new_session") + " (" + t("sessions.input_title_prompt") + "):",
                default="",
            ).unsafe_ask()
        except KeyboardInterrupt:
            # 用户取消
            console.print(f"\n[dim]{t('sessions.actions.cancelled')}[/dim]")
            return

        # 获取下一个可用的数字 ID
        next_id = self._get_next_session_id()
        session_id = f"session_{next_id}"

        # 用户输入的作为标题（如果为空则标题为空字符串）
        title = new_name.strip() if new_name.strip() else ""

        # 创建新会话记录
        if not self.store.session_exists(session_id):
            self.store.create_session(session_id, title=title)

        console.print(
            f"[green]✓ {t('sessions.actions.enter_chat')}: {session_id} ({title})[/green]\n"
        )
        config_obj = self._load_config()
        ws_path = Path(config_obj.agents.defaults.workspace).expanduser()
        _run_chat_session(session_id, None, str(ws_path))
        # 聊天结束后返回，由调用者处理列表刷新

    def _get_next_session_id(self) -> int:
        """获取下一个可用的会话 ID 序号.

        Returns:
            下一个可用的数字 ID（从 1 开始）
        """
        sessions = self.store.get_all_sessions()
        if not sessions:
            return 1

        # 提取现有的数字 ID
        existing_ids = set()
        for session in sessions:
            if session.session_id.startswith("session_"):
                try:
                    num = int(session.session_id.split("_")[1])
                    existing_ids.add(num)
                except (IndexError, ValueError):
                    pass

        # 找到第一个缺失的数字
        next_id = 1
        while next_id in existing_ids:
            next_id += 1
        return next_id

    def _confirm_and_delete(self, session_id: str) -> bool:
        """确认并删除会话.

        Args:
            session_id: 会话 ID

        Returns:
            是否成功删除
        """
        confirm = questionary.confirm(
            t("sessions.actions.confirm_delete", session_id=session_id),
            default=False,
        ).unsafe_ask()

        if confirm:
            self.store.delete_session(session_id)
            self._delete_checkpoint_data(session_id)
            console.print(
                f"[green]{t('sessions.actions.delete_success', session_id=session_id)}[/green]"
            )
            return True
        else:
            console.print(t("sessions.actions.delete_cancelled"))
            return False

    def _rearrange_session_ids(self) -> None:
        """重新排列会话 ID.

        删除会话后，按创建时间排序并重新分配数字 ID（1, 2, 3...）
        """
        sessions = self.store.get_all_sessions()

        # 按创建时间排序
        sorted_sessions = sorted(sessions, key=lambda s: s.created_at)

        # 重新分配 ID：session_1, session_2, ...
        for new_id, session in enumerate(sorted_sessions, start=1):
            new_session_id = f"session_{new_id}"
            if session.session_id != new_session_id:
                # 更新会话 ID
                self._update_session_id(session.session_id, new_session_id)

    def _update_session_id(self, old_id: str, new_id: str) -> None:
        """更新会话 ID.

        Args:
            old_id: 旧会话 ID
            new_id: 新会话 ID
        """
        import sqlite3
        from contextlib import closing

        db_path = self.workspace / "sessions_metadata.db"
        if not db_path.exists():
            return

        try:
            with closing(sqlite3.connect(str(db_path))) as conn:
                cursor = conn.cursor()
                # 更新元数据表
                cursor.execute(
                    "UPDATE sessions SET session_id = ? WHERE session_id = ?",
                    (new_id, old_id),
                )
                conn.commit()

                # 同时更新 checkpoint 数据
                self._update_checkpoint_session_id(old_id, new_id)

                logger.debug(f"Updated session ID: {old_id} -> {new_id}")
        except Exception as e:
            logger.warning(f"Failed to update session ID from {old_id} to {new_id}: {e}")

    def _update_checkpoint_session_id(self, old_id: str, new_id: str) -> None:
        """更新 checkpoint 数据中的会话 ID.

        Args:
            old_id: 旧会话 ID
            new_id: 新会话 ID
        """
        import sqlite3
        from contextlib import closing

        db_path = self.workspace / "checkpoints.db"
        if not db_path.exists():
            return

        try:
            with closing(sqlite3.connect(str(db_path))) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE checkpoints SET thread_id = ? WHERE thread_id = ?",
                    (new_id, old_id),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update checkpoint session ID from {old_id} to {new_id}: {e}")

    def _rename_session(self, session_id: str) -> None:
        """重命名会话.

        Args:
            session_id: 会话 ID
        """
        session = self.store.get_session(session_id)
        if not session:
            console.print(f"[red]Session '{session_id}' not found[/red]")
            return

        new_title = questionary.text(
            f"{t('sessions.actions.rename')} ({t('cli.config.current')} {session.title}):",
            default=session.title,
        ).unsafe_ask()

        if new_title and new_title.strip() and new_title.strip() != session.title:
            self.store.update_activity(session_id, title=new_title.strip())
            console.print(
                f"[green]{t('sessions.actions.rename_success', title=new_title.strip())}[/green]"
            )

    def _load_config(self):
        """加载配置（避免循环导入）."""
        from finchbot.config import load_config

        return load_config()

    def _delete_checkpoint_data(self, session_id: str) -> None:
        """删除会话的 checkpoint 数据.

        Args:
            session_id: 会话 ID
        """
        import sqlite3
        from contextlib import closing

        db_path = self.workspace / "checkpoints.db"
        if not db_path.exists():
            return

        try:
            with closing(sqlite3.connect(str(db_path))) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (session_id,))
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to delete checkpoint data for {session_id}: {e}")

    def select_and_manage(self) -> tuple[str | None, str]:
        """显示交互式会话管理界面（向后兼容）.

        支持选择、删除、重命名操作。

        Returns:
            (session_id, action) 元组，action 为 'select'、'delete'、'new' 或 'quit'
        """
        sessions = self.store.get_all_sessions()

        if not sessions:
            console.print(t("sessions.no_sessions"))
            # 询问是否创建新会话
            create_new = questionary.confirm(
                t("sessions.new_session") + "?",
                default=True,
            ).unsafe_ask()
            if create_new:
                return self._create_new_session(), "new"
            return None, "quit"

        # 先显示美观的会话列表
        console.print()
        table = self.renderer.render_table(sessions)
        console.print(table)
        console.print()

        # 构建选项列表
        choices = [
            questionary.Choice(
                title=f"🆕 {t('sessions.new_session')}",
                value="__new__",
            ),
        ]

        choices.extend(
            [
                questionary.Choice(
                    title=self._format_session_choice(session),
                    value=session.session_id,
                )
                for session in sessions
            ]
        )

        try:
            # 使用 unsafe_ask 而不是 ask，避免某些终端的输入流问题
            selected = questionary.select(
                f"{t('sessions.actions.select')} ({t('sessions.help.q_quit')}):",
                choices=choices,
                use_arrow_keys=True,
                use_jk_keys=False,
                use_emacs_keys=False,
            ).unsafe_ask()

            if selected is None:
                return None, "quit"

            if selected == "__new__":
                return self._create_new_session(), "new"

            # 返回选中的会话，由调用者决定后续操作
            return selected, "select"

        except KeyboardInterrupt:
            logger.debug("Session selection cancelled by user")
            return None, "quit"

    def delete_session_interactive(self, session_id: str | None = None) -> bool:
        """交互式删除会话.

        Args:
            session_id: 要删除的会话 ID，如为 None 则先让用户选择

        Returns:
            是否成功删除
        """
        if session_id is None:
            sessions = self.store.get_all_sessions()

            if not sessions:
                console.print(t("sessions.no_sessions"))
                return False

            choices = [
                questionary.Choice(
                    title=self._format_session_choice(session),
                    value=session.session_id,
                )
                for session in sessions
            ]

            try:
                selected = questionary.select(
                    t("sessions.actions.delete") + ":",
                    choices=choices,
                    use_arrow_keys=True,
                ).unsafe_ask()

                if not selected:
                    return False

                session_id = selected

            except KeyboardInterrupt:
                return False

        # 确认删除
        if session_id is None:
            return False

        confirm = questionary.confirm(
            t("sessions.actions.confirm_delete", session_id=session_id),
            default=False,
        ).unsafe_ask()

        if confirm:
            self.store.delete_session(session_id)
            console.print(
                f"[green]{t('sessions.actions.delete_success', session_id=session_id)}[/green]"
            )
            return True

        console.print(t("sessions.actions.delete_cancelled"))
        return False

    def rename_session(self, session_id: str | None = None) -> bool:
        """重命名会话.

        Args:
            session_id: 要重命名的会话 ID，如为 None 则先让用户选择

        Returns:
            是否成功重命名
        """
        if session_id is None:
            sessions = self.store.get_all_sessions()

            if not sessions:
                console.print(t("sessions.no_sessions"))
                return False

            choices = [
                questionary.Choice(
                    title=self._format_session_choice(session),
                    value=session.session_id,
                )
                for session in sessions
            ]

            try:
                selected = questionary.select(
                    t("sessions.actions.rename") + ":",
                    choices=choices,
                    use_arrow_keys=True,
                ).unsafe_ask()

                if not selected:
                    return False

                session_id = selected

            except KeyboardInterrupt:
                return False

        if session_id is None:
            return False

        session = self.store.get_session(session_id)
        if not session:
            console.print(f"[red]Session '{session_id}' not found[/red]")
            return False

        new_title = questionary.text(
            f"{t('sessions.actions.rename')} ({t('cli.config.current')} {session.title}):",
            default=session.title,
        ).unsafe_ask()

        if new_title and new_title.strip() and new_title.strip() != session.title:
            self.store.update_activity(session_id, title=new_title.strip())
            console.print(
                f"[green]{t('sessions.actions.rename_success', title=new_title.strip())}[/green]"
            )
            return True

        return False

    def select_or_create(self) -> str:
        """选择现有会话或创建新会话（向后兼容）.

        Returns:
            选中的或新创建的 session_id
        """
        session_id, action = self.select_and_manage()

        if action == "quit" or session_id is None:
            return "default"

        return session_id

    def select_session(self, sessions: "Sequence[SessionMetadata]") -> str | None:
        """显示交互式选择界面（向后兼容）.

        Args:
            sessions: 会话列表

        Returns:
            选中的 session_id，如取消则返回 None
        """
        if not sessions:
            console.print(t("sessions.no_sessions"))
            return None

        choices = [
            questionary.Choice(
                title=self._format_session_choice(session),
                value=session.session_id,
            )
            for session in sessions
        ]

        try:
            selected = questionary.select(
                t("sessions.actions.select") + ":",
                choices=choices,
                use_arrow_keys=True,
                use_jk_keys=False,
                use_emacs_keys=False,
            ).unsafe_ask()

            return selected

        except KeyboardInterrupt:
            logger.debug("Session selection cancelled by user")
            return None

    def display_session_list(self) -> None:
        """显示美观的会话列表（只读）."""
        sessions = self.store.get_all_sessions()

        if not sessions:
            console.print(self.renderer.render_empty())
            return

        table = self.renderer.render_table(sessions)
        console.print(table)
        console.print(f"\n[dim]{t('sessions.session_count', count=len(sessions))}[/dim]")
