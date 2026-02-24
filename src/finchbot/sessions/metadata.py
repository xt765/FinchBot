"""会话元数据管理.

管理会话的元数据信息，包括标题、创建时间、最后活跃时间等。
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class SessionMetadata:
    """会话元数据.

    Attributes:
        session_id: 会话ID (thread_id)
        title: 会话标题（自动生成或用户自定义）
        created_at: 创建时间
        last_active: 最后活跃时间
        message_count: 消息数量
        turn_count: 会话轮次（一问一答算一轮）
    """

    session_id: str
    title: str
    created_at: datetime
    last_active: datetime
    message_count: int = 0
    turn_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "message_count": self.message_count,
            "turn_count": self.turn_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMetadata":
        """从字典创建."""
        return cls(
            session_id=data["session_id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
            message_count=data.get("message_count", 0),
            turn_count=data.get("turn_count", 0),
        )


class SessionMetadataStore:
    """会话元数据存储.

    使用 SQLite 存储会话元数据，与 checkpoints 表分开存储。
    """

    def __init__(self, workspace: Path) -> None:
        """初始化存储.

        Args:
            workspace: 工作目录路径
        """
        self.workspace = Path(workspace)
        self.db_path = self.workspace / "sessions_metadata.db"
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表."""
        self.workspace.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    turn_count INTEGER DEFAULT 0
                )
            """)
            # 数据库迁移：检查 turn_count 列是否存在，如不存在则添加
            cursor = conn.execute("PRAGMA table_info(sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            if "turn_count" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN turn_count INTEGER DEFAULT 0")
            conn.commit()
        logger.debug(f"Session metadata store initialized at {self.db_path}")

    def create_session(
        self, session_id: str, title: str | None = None, message_count: int = 0, turn_count: int = 0
    ) -> SessionMetadata:
        """创建新会话记录.

        Args:
            session_id: 会话ID
            title: 会话标题，如未提供则使用 session_id
            message_count: 初始消息数量
            turn_count: 初始会话轮次

        Returns:
            创建的会话元数据
        """
        now = datetime.now()
        metadata = SessionMetadata(
            session_id=session_id,
            title=title or session_id,
            created_at=now,
            last_active=now,
            message_count=message_count,
            turn_count=turn_count,
        )

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, title, created_at, last_active, message_count, turn_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    metadata.session_id,
                    metadata.title,
                    metadata.created_at.isoformat(),
                    metadata.last_active.isoformat(),
                    metadata.message_count,
                    metadata.turn_count,
                ),
            )
            conn.commit()

        logger.debug(f"Created session metadata: {session_id}")
        return metadata

    def update_activity(
        self,
        session_id: str,
        title: str | None = None,
        message_count: int | None = None,
        turn_count: int | None = None,
    ) -> None:
        """更新会话活跃时间.

        Args:
            session_id: 会话ID
            title: 新的标题（可选）
            message_count: 新的消息数量（可选）
            turn_count: 新的会话轮次（可选）
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            if turn_count is not None:
                conn.execute(
                    "UPDATE sessions SET last_active = ?, turn_count = ? WHERE session_id = ?",
                    (now, turn_count, session_id),
                )
            elif title is not None and message_count is not None:
                conn.execute(
                    """
                    UPDATE sessions
                    SET last_active = ?, title = ?, message_count = ?
                    WHERE session_id = ?
                """,
                    (now, title, message_count, session_id),
                )
            elif title is not None:
                conn.execute(
                    """
                    UPDATE sessions
                    SET last_active = ?, title = ?
                    WHERE session_id = ?
                """,
                    (now, title, session_id),
                )
            elif message_count is not None:
                conn.execute(
                    """
                    UPDATE sessions
                    SET last_active = ?, message_count = ?
                    WHERE session_id = ?
                """,
                    (now, message_count, session_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE sessions
                    SET last_active = ?
                    WHERE session_id = ?
                """,
                    (now, session_id),
                )
            conn.commit()

        logger.debug(f"Updated session activity: {session_id}")

    def get_session(self, session_id: str) -> SessionMetadata | None:
        """获取会话元数据.

        Args:
            session_id: 会话ID

        Returns:
            会话元数据，如不存在则返回 None
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()

        if row is None:
            return None

        return SessionMetadata(
            session_id=row[0],
            title=row[1],
            created_at=datetime.fromisoformat(row[2]),
            last_active=datetime.fromisoformat(row[3]),
            message_count=row[4],
            turn_count=row[5] if len(row) > 5 else 0,
        )

    def list_sessions(self) -> list[SessionMetadata]:
        """获取所有会话元数据列表.

        Returns:
            按最后活跃时间倒序排列的会话列表。
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                ORDER BY last_active DESC
            """
            )
            rows = cursor.fetchall()

        return [
            SessionMetadata(
                session_id=row[0],
                title=row[1],
                created_at=datetime.fromisoformat(row[2]),
                last_active=datetime.fromisoformat(row[3]),
                message_count=row[4],
                turn_count=row[5] if len(row) > 5 else 0,
            )
            for row in rows
        ]

    def get_all_sessions(self) -> list[SessionMetadata]:
        """获取所有会话元数据.

        Returns:
            按 session_id 数字顺序排列的会话列表
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                ORDER BY
                    CASE
                        WHEN session_id LIKE 'session_%' THEN CAST(SUBSTR(session_id, 9) AS INTEGER)
                        ELSE 2147483647
                    END
            """
            )
            rows = cursor.fetchall()

        return [
            SessionMetadata(
                session_id=row[0],
                title=row[1],
                created_at=datetime.fromisoformat(row[2]),
                last_active=datetime.fromisoformat(row[3]),
                message_count=row[4],
                turn_count=row[5] if len(row) > 5 else 0,
            )
            for row in rows
        ]

    def delete_session(self, session_id: str) -> bool:
        """删除会话元数据.

        Args:
            session_id: 会话ID

        Returns:
            是否成功删除
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.debug(f"Deleted session metadata: {session_id}")
        return deleted

    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在.

        Args:
            session_id: 会话ID

        Returns:
            是否存在
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
            return cursor.fetchone() is not None

    def get_next_session_id(self) -> str:
        """生成下一个可用的会话 ID，格式为 session_N。

        Returns:
            下一个可用的会话 ID
        """
        sessions = self.get_all_sessions()
        existing_ids = set()
        for session in sessions:
            if session.session_id.startswith("session_"):
                try:
                    num = int(session.session_id.split("_")[1])
                    existing_ids.add(num)
                except (IndexError, ValueError):
                    pass

        next_id = 1
        while next_id in existing_ids:
            next_id += 1
        return f"session_{next_id}"
