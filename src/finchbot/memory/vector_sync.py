"""向量存储同步管理.

负责SQLite数据库和向量存储之间的数据同步。
"""

from datetime import datetime
from typing import Any

from loguru import logger

from finchbot.memory.storage.sqlite import SQLiteStore
from finchbot.memory.storage.vector import VectorMemoryStore


class DataSyncManager:
    """数据同步管理器.

    负责SQLite和向量存储之间的数据同步，保证数据一致性。
    简化版本：移除异步队列，改为直接同步操作。
    """

    def __init__(
        self,
        sqlite_store: SQLiteStore,
        vector_store: VectorMemoryStore | None,
        max_retries: int = 2,
    ) -> None:
        """初始化数据同步管理器.

        Args:
            sqlite_store: SQLite存储实例。
            vector_store: 向量存储实例。
            max_retries: 最大重试次数。
        """
        self.sqlite_store = sqlite_store
        self.vector_store = vector_store
        self.max_retries = max_retries

        # 简化状态跟踪
        self.sync_stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "last_error": None,
            "last_sync_time": None,
        }

        logger.info("DataSyncManager initialized (simplified version)")

    def sync_memory(self, memory_id: str, operation: str) -> bool | None:
        """同步单个记忆.

        优化版：添加智能重试机制，提高成功率。

        Args:
            memory_id: 记忆ID。
            operation: 操作类型 ('add', 'update', 'delete')。

        Returns:
            是否成功同步。
        """
        self.sync_stats["total_syncs"] += 1

        # 重试机制
        for attempt in range(self.max_retries + 1):
            try:
                if operation == "delete":
                    # 从向量存储删除
                    if self.vector_store:
                        success = self.vector_store.delete(ids=[memory_id])
                        if success:
                            self.sync_stats["successful_syncs"] += 1
                            logger.debug(f"Deleted from vector store: {memory_id[:8]}...")
                        else:
                            if attempt < self.max_retries:
                                logger.debug(
                                    f"Delete failed, retrying ({attempt + 1}/{self.max_retries}): {memory_id[:8]}..."
                                )
                                continue
                            self.sync_stats["failed_syncs"] += 1
                            logger.warning(
                                f"Failed to delete from vector store: {memory_id[:8]}..."
                            )
                        return success
                    return True

                # 获取记忆详情
                memory = self.sqlite_store.get_memory(memory_id)
                if not memory:
                    logger.warning(f"Memory not found for sync: {memory_id[:8]}...")
                    self.sync_stats["failed_syncs"] += 1
                    return False

                # 同步到向量存储
                if self.vector_store:
                    try:
                        success = False
                        if operation == "add":
                            success = self.vector_store.remember(
                                content=memory["content"],
                                metadata={
                                    "id": memory_id,
                                    "category": memory["category"],
                                    "importance": memory["importance"],
                                    "source": memory["source"],
                                    "created_at": memory["created_at"],
                                },
                                id=memory_id,
                            )
                        elif operation == "update":
                            # 先删除旧的（如果存在）
                            self.vector_store.delete(ids=[memory_id])
                            # 再添加新的
                            success = self.vector_store.remember(
                                content=memory["content"],
                                metadata={
                                    "id": memory_id,
                                    "category": memory["category"],
                                    "importance": memory["importance"],
                                    "source": memory["source"],
                                    "updated_at": memory["updated_at"],
                                },
                                id=memory_id,
                            )
                        else:
                            logger.warning(f"Unknown operation: {operation}")
                            self.sync_stats["failed_syncs"] += 1
                            return False

                        if success:
                            self.sync_stats["successful_syncs"] += 1
                            logger.debug(f"Synced to vector store: {operation} {memory_id[:8]}...")
                        else:
                            if attempt < self.max_retries:
                                logger.debug(
                                    f"Sync failed, retrying ({attempt + 1}/{self.max_retries}): {memory_id[:8]}..."
                                )
                                continue
                            self.sync_stats["failed_syncs"] += 1
                            logger.warning(
                                f"Failed to sync to vector store: {operation} {memory_id[:8]}..."
                            )

                        return success
                    except Exception as e:
                        if attempt < self.max_retries:
                            logger.debug(
                                f"Vector store error, retrying ({attempt + 1}/{self.max_retries}): {e}"
                            )
                            continue
                        # 向量存储错误时，仍视为成功（SQLite已保存）
                        logger.warning(f"Vector store error, but memory saved to SQLite: {e}")
                        return True

                # 如果没有向量存储，也视为成功（离线模式）
                return True

            except Exception as e:
                if attempt < self.max_retries:
                    logger.debug(f"Sync error, retrying ({attempt + 1}/{self.max_retries}): {e}")
                    continue

                error_msg = str(e)
                self.sync_stats["failed_syncs"] += 1
                self.sync_stats["last_error"] = error_msg
                logger.error(f"Sync memory error for {memory_id[:8]}...: {e}")
                return False
            finally:
                self.sync_stats["last_sync_time"] = datetime.now().isoformat()

    def get_sync_status(self) -> dict[str, Any]:
        """获取同步状态.

        Returns:
            同步状态字典。
        """
        return self.sync_stats.copy()

    def stop(self) -> None:
        """停止同步管理器."""
        logger.info("DataSyncManager stopped")

    def __enter__(self):
        """上下文管理器入口."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口."""
        self.stop()
