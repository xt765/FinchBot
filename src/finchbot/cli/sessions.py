"""会话管理命令行模块.

提供会话显示和回退功能。
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime

import questionary

from finchbot.cli import console
from finchbot.i18n import t


def show_session(
    session_id: str,
    limit: int,
    show_index: bool,
) -> None:
    """显示会话历史.

    Args:
        session_id: 会话 ID
        limit: 最大显示消息数
        show_index: 是否显示消息索引
    """
    from finchbot.agent import get_default_workspace
    ws_path = get_default_workspace()
    db_path = ws_path / "checkpoints.db"

    if not db_path.exists():
        console.print("[yellow]No sessions database found.[/yellow]")
        return

    try:
        with closing(sqlite3.connect(str(db_path))) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT checkpoint FROM checkpoints
                WHERE thread_id = ?
                ORDER BY checkpoint_id DESC
                LIMIT ?
            """,
                (session_id, limit),
            )
            checkpoints = cursor.fetchall()

        if not checkpoints:
            console.print(f"[yellow]No history found for session '{session_id}'.[/yellow]")
            return

        console.print(f"[bold cyan]📜 Session: {session_id}[/bold cyan]\n")

        messages = []
        for (checkpoint_json,) in checkpoints:
            try:
                data = json.loads(checkpoint_json)
                if "channel_values" in data and "messages" in data["channel_values"]:
                    messages.extend(data["channel_values"]["messages"])
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        seen = set()
        unique_messages = []
        for msg in reversed(messages[-limit * 2 :]):
            content = msg.get("content", "")
            if content and content not in seen:
                seen.add(content)
                unique_messages.append(msg)

        for idx, msg in enumerate(unique_messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", None)

            prefix = f"[{idx}] " if show_index else ""

            if role == "user":
                display_content = content[:200] + "..." if len(content) > 200 else content
                console.print(f"{prefix}[cyan]👤 {t('cli.history.role_you')}: [cyan]{display_content}[/cyan]")
            elif role == "assistant":
                display_content = content[:200] + "..." if len(content) > 200 else content
                console.print(f"{prefix}[green]🤖 {t('cli.history.role_bot')}: [green]{display_content}[/green]")
            elif tool_calls:
                tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                tool_info = f" [{', '.join(tool_names)}]" if tool_names else ""
                console.print(f"{prefix}[yellow]🔧 {t('cli.history.role_tool')}:[/yellow] {tool_info}")
            console.print()

        if show_index:
            console.print(
                f"[dim]Tip: Use 'sessions rollback {session_id} <index> --new-session <name>'[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error reading session: {e}[/red]")


def rollback_session(
    session_id: str,
    message_index: int,
    new_session: str | None,
    force: bool,
) -> None:
    """回退到指定消息之前，可选创建新会话.

    Args:
        session_id: 要回退的会话 ID
        message_index: 消息索引（回退到此索引之前）
        new_session: 新会话名称（可选）
        force: 强制执行不确认
    """
    from finchbot.agent import get_default_workspace
    ws_path = get_default_workspace()
    db_path = ws_path / "checkpoints.db"

    if not db_path.exists():
        console.print("[yellow]No sessions database found.[/yellow]")
        return

    try:
        with closing(sqlite3.connect(str(db_path))) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT checkpoint_id, checkpoint FROM checkpoints
                WHERE thread_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            )
            result = cursor.fetchone()

            if not result:
                console.print(f"[yellow]Session '{session_id}' not found.[/yellow]")
                return

            checkpoint_id, checkpoint_json = result
            checkpoint_data = json.loads(checkpoint_json)
            messages = checkpoint_data.get("channel_values", {}).get("messages", [])

            if message_index < 0 or message_index > len(messages):
                console.print(f"[red]Invalid message index. Range: 0-{len(messages)}[/red]")
                return

            if not force:
                keep_count = message_index
                remove_start = message_index
                remove_end = len(messages) - 1
                remove_count = len(messages) - message_index
                rollback_msg = t('sessions.rollback.confirm_rollback').format(message_index)
                keep_msg = t('sessions.rollback.keep_messages').format(message_index - 1, keep_count)
                remove_msg = t('sessions.rollback.remove_messages').format(remove_start, remove_end, remove_count)
                confirm_msg = f"{rollback_msg} {keep_msg}, {remove_msg}."
                confirm = questionary.confirm(confirm_msg, default=False).ask()
                if not confirm:
                    console.print(f"[dim]{t('sessions.rollback.cancelled')}[/dim]")
                    return

            rolled_back_messages = messages[:message_index]

            if new_session:
                new_checkpoint = {
                    "channel_values": {"messages": rolled_back_messages},
                    "metadata": {
                        "source_session": session_id,
                        "source_checkpoint": checkpoint_id,
                        "rollback_to": message_index,
                        "created_at": datetime.now().isoformat(),
                    },
                }

                cursor.execute(
                    """
                    INSERT INTO checkpoints
                    (thread_id, checkpoint_id, checkpoint, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        new_session,
                        f"rollback-{datetime.now().timestamp()}",
                        json.dumps(new_checkpoint),
                        json.dumps({"source": session_id, "rollback": True}),
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()

                console.print(
                    f"[green]✓ Created new session '{new_session}' "
                    f"with {len(rolled_back_messages)} messages[/green]"
                )
                console.print(
                    f"[dim]Rolled back from message {message_index} of '{session_id}'[/dim]"
                )
                console.print(f"[dim]Start chatting: finchbot repl -s {new_session}[/dim]")
            else:
                new_checkpoint = {
                    "channel_values": {"messages": rolled_back_messages},
                    "metadata": checkpoint_data.get("metadata", {}),
                }
                new_checkpoint["metadata"]["rolled_back"] = {
                    "from_index": message_index,
                    "original_count": len(messages),
                    "rolled_at": datetime.now().isoformat(),
                }

                cursor.execute(
                    """
                    UPDATE checkpoints
                    SET checkpoint = ?, metadata = ?
                    WHERE thread_id = ? AND checkpoint_id = ?
                    """,
                    (
                        json.dumps(new_checkpoint),
                        json.dumps(new_checkpoint["metadata"]),
                        session_id,
                        checkpoint_id,
                    ),
                )
                conn.commit()

                kept = len(rolled_back_messages)
                removed = len(messages) - message_index
                console.print(
                    f"[green]✓ Rolled back session '{session_id}' "
                    f"to message {message_index}[/green]"
                )
                console.print(f"[dim]Kept {kept} messages, removed {removed}[/dim]")

    except Exception as e:
        console.print(f"[red]Error rolling back session: {e}[/red]")
