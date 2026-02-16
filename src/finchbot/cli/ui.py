"""CLI UI 组件.

提供通用的命令行 UI 组件，包括键盘导航选择器等交互式界面。
"""

from __future__ import annotations

from typing import Any

import readchar
from rich.console import Console

console = Console()


def _keyboard_select(
    items: list[dict],
    title: str,
    help_text: str,
    allow_quit: bool = True,
    initial_idx: int = 0,
) -> Any | None:
    """通用键盘导航选择器.

    Args:
        items: 选项列表，每项包含 'name' 和 'value'
        title: 界面标题（已包含样式）
        help_text: 底部帮助文本（已包含样式）
        allow_quit: 是否允许按 Q 退出
        initial_idx: 初始选中项索引

    Returns:
        选中项的 value，或 None（如果用户退出）
    """
    selected_idx = initial_idx

    try:
        while True:
            console.clear()
            console.print(title)

            for idx, item in enumerate(items):
                is_selected = idx == selected_idx
                cursor = "▶" if is_selected else "  "
                if is_selected:
                    console.print(f"{cursor} [cyan bold]{item['name']}[/cyan bold]")
                else:
                    console.print(f"{cursor} {item['name']}")

            console.print(help_text)

            key = readchar.readkey()

            if key == readchar.key.UP:
                selected_idx = max(0, selected_idx - 1)
            elif key == readchar.key.DOWN:
                selected_idx = min(len(items) - 1, selected_idx + 1)
            elif key == readchar.key.ENTER:
                return items[selected_idx]["value"]
            elif allow_quit and key.lower() == "q":
                return None
            elif key == readchar.key.CTRL_C:
                raise KeyboardInterrupt

    except KeyboardInterrupt:
        raise
