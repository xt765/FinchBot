"""SQLite存储层实现.

作为记忆系统的唯一真相源，提供ACID保证的数据存储。
"""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from loguru import logger


class SQLiteStore:
    """SQLite存储实现.

    提供记忆数据的持久化存储，作为系统的唯一真相源。
    """

    def __init__(self, db_path: Path) -> None:
        """初始化SQLite存储.

        Args:
            db_path: 数据库文件路径。
        """
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """获取新的数据库连接.

        Returns:
            SQLite连接对象。
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        """初始化数据库表."""
        with self._get_connection() as connection:
            # 记忆核心表
            connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    importance REAL DEFAULT 0.5,
                    source TEXT DEFAULT 'manual',
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    is_archived BOOLEAN DEFAULT FALSE,
                    archived_at TIMESTAMP
                )
            """)

            # 分类表
            connection.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    keywords TEXT DEFAULT '[]',
                    parent_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES categories(id)
                )
            """)

            # 访问日志表
            connection.execute("""
                CREATE TABLE IF NOT EXISTS memory_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    access_type TEXT NOT NULL,
                    access_context TEXT,
                    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (memory_id) REFERENCES memories(id)
                )
            """)

            # 创建索引
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_is_archived ON memories(is_archived)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_access_log_memory_id ON memory_access_log(memory_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_access_log_accessed_at ON memory_access_log(accessed_at)"
            )

        logger.info(f"SQLite tables initialized at {self.db_path}")

    def remember(
        self,
        content: str,
        category: str = "general",
        importance: float = 0.5,
        source: str = "manual",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """添加记忆.

        Args:
            content: 记忆内容。
            category: 分类标签。
            importance: 重要性评分 (0-1)。
            source: 来源。
            tags: 标签列表。
            metadata: 元数据。

        Returns:
            记忆ID。
        """
        memory_id = str(uuid.uuid4())
        tags_json = json.dumps(tags or [])
        metadata_json = json.dumps(metadata or {})

        with self._get_connection() as connection:
            connection.execute(
                """
                INSERT INTO memories (id, content, category, importance, source, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (memory_id, content, category, importance, source, tags_json, metadata_json),
            )

        logger.debug(
            f"Memory added: {memory_id[:8]}... (category: {category}, importance: {importance})"
        )
        return memory_id

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """获取记忆详情.

        Args:
            memory_id: 记忆ID。

        Returns:
            记忆字典，如果不存在返回None。
        """
        with self._get_connection() as connection:
            cursor = connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return self._row_to_dict(row)

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        category: str | None = None,
        importance: float | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """更新记忆.

        Args:
            memory_id: 记忆ID。
            content: 新的内容。
            category: 新的分类。
            importance: 新的重要性评分。
            tags: 新的标签列表。
            metadata: 新的元数据。

        Returns:
            是否成功更新。
        """
        # 构建更新字段
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)

        if category is not None:
            updates.append("category = ?")
            params.append(category)

        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)

        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(memory_id)

        with self._get_connection() as connection:
            cursor = connection.execute(
                f"UPDATE memories SET {', '.join(updates)} WHERE id = ?",
                params,
            )

        updated = cursor.rowcount > 0
        if updated:
            logger.debug(f"Memory updated: {memory_id[:8]}...")
        return updated

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆.

        Args:
            memory_id: 记忆ID。

        Returns:
            是否成功删除。
        """
        with self._get_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE id = ?",
                (memory_id,),
            )

        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"Memory deleted: {memory_id[:8]}...")
        return deleted

    def archive_memory(self, memory_id: str) -> bool:
        """归档记忆.

        Args:
            memory_id: 记忆ID。

        Returns:
            是否成功归档。
        """
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE memories
                SET is_archived = TRUE, archived_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (memory_id,),
            )

        archived = cursor.rowcount > 0
        if archived:
            logger.debug(f"Memory archived: {memory_id[:8]}...")
        return archived

    def unarchive_memory(self, memory_id: str) -> bool:
        """取消归档记忆.

        Args:
            memory_id: 记忆ID。

        Returns:
            是否成功取消归档。
        """
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE memories
                SET is_archived = FALSE, archived_at = NULL
                WHERE id = ?
                """,
                (memory_id,),
            )

        unarchived = cursor.rowcount > 0
        if unarchived:
            logger.debug(f"Memory unarchived: {memory_id[:8]}...")
        return unarchived

    def record_access(
        self,
        memory_id: str,
        access_type: str,
        access_context: str | None = None,
    ) -> None:
        """记录访问日志.

        Args:
            memory_id: 记忆ID。
            access_type: 访问类型 ('read', 'write', 'delete')。
            access_context: 访问上下文。
        """
        with self._get_connection() as connection:
            # 记录访问日志
            connection.execute(
                """
                INSERT INTO memory_access_log (memory_id, access_type, access_context)
                VALUES (?, ?, ?)
                """,
                (memory_id, access_type, access_context),
            )

            # 更新记忆的访问统计
            connection.execute(
                """
                UPDATE memories
                SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE id = ?
                """,
                (memory_id,),
            )

    def search_memories(
        self,
        query: str | None = None,
        category: str | None = None,
        min_importance: float = 0.0,
        max_importance: float = 1.0,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """搜索记忆.

        Args:
            query: 关键词查询。
            category: 分类过滤。
            min_importance: 最小重要性。
            max_importance: 最大重要性。
            include_archived: 是否包含归档的记忆。
            limit: 返回数量限制。
            offset: 偏移量。

        Returns:
            记忆列表。
        """
        conditions = ["1=1"]
        params = []

        if query:
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")

        if category:
            conditions.append("category = ?")
            params.append(category)

        conditions.append("importance >= ?")
        params.append(min_importance)

        conditions.append("importance <= ?")
        params.append(max_importance)

        if not include_archived:
            conditions.append("is_archived = FALSE")

        sql = f"""
            SELECT * FROM memories
            WHERE {" AND ".join(conditions)}
            ORDER BY importance DESC, created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with self._get_connection() as connection:
            cursor = connection.execute(sql, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_recent_memories(
        self,
        days: int = 7,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """获取最近添加的记忆.

        Args:
            days: 最近天数。
            limit: 返回数量限制。

        Returns:
            记忆列表。
        """
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                SELECT * FROM memories
                WHERE created_at >= datetime('now', ?)
                AND is_archived = FALSE
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"-{days} days", limit),
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_important_memories(
        self,
        min_importance: float = 0.8,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """获取重要记忆.

        Args:
            min_importance: 最小重要性阈值。
            limit: 返回数量限制。

        Returns:
            记忆列表。
        """
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                SELECT * FROM memories
                WHERE importance >= ?
                AND is_archived = FALSE
                ORDER BY importance DESC, access_count DESC
                LIMIT ?
                """,
                (min_importance, limit),
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_memory_stats(self) -> dict[str, Any]:
        """获取记忆统计信息.

        Returns:
            统计字典。
        """
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_archived = TRUE THEN 1 END) as archived,
                    COUNT(CASE WHEN importance >= 0.8 THEN 1 END) as important,
                    AVG(importance) as avg_importance,
                    SUM(access_count) as total_accesses,
                    MAX(created_at) as latest_created,
                    MAX(last_accessed) as latest_accessed
                FROM memories
                """
            )
            row = cursor.fetchone()
            return dict(row) if row else {}

    def add_category(
        self,
        name: str,
        description: str | None = None,
        keywords: list[str] | None = None,
        parent_id: str | None = None,
    ) -> str:
        """添加分类.

        Args:
            name: 分类名称。
            description: 分类描述。
            keywords: 关键词列表。
            parent_id: 父分类ID。

        Returns:
            分类ID。
        """
        category_id = str(uuid.uuid4())
        keywords_json = json.dumps(keywords or [])

        with self._get_connection() as connection:
            connection.execute(
                """
                INSERT INTO categories (id, name, description, keywords, parent_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (category_id, name, description, keywords_json, parent_id),
            )

        logger.debug(f"Category added: {name} (id: {category_id[:8]}...)")
        return category_id

    def get_categories(self) -> list[dict[str, Any]]:
        """获取所有分类.

        Returns:
            分类列表。
        """
        with self._get_connection() as connection:
            cursor = connection.execute("SELECT * FROM categories ORDER BY name")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """将SQLite行转换为字典.

        Args:
            row: SQLite行对象。

        Returns:
            字典。
        """
        result = dict(row)

        # 解析JSON字段
        if "tags" in result and result["tags"]:
            result["tags"] = json.loads(result["tags"])
        else:
            result["tags"] = []

        if "metadata" in result and result["metadata"]:
            result["metadata"] = json.loads(result["metadata"])
        else:
            result["metadata"] = {}

        if "keywords" in result and result["keywords"]:
            result["keywords"] = json.loads(result["keywords"])
        else:
            result["keywords"] = []

        # 转换SQLite布尔值为Python布尔值
        if "is_archived" in result:
            result["is_archived"] = bool(result["is_archived"])

        return result

    def close(self) -> None:
        """关闭数据库连接."""
        logger.debug("SQLiteStore closed")

    def __enter__(self):
        """上下文管理器入口."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口."""
        self.close()
