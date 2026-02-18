"""向量存储同步管理.

负责SQLite数据库和向量存储之间的数据同步。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class DataSyncManager:
    """数据同步管理器.

    负责SQLite和向量存储之间的数据同步，保证数据一致性。
    简化版本：移除异步队列，改为直接同步操作。
    """

    def __init__(
        self,
        sqlite_store: Any,
        vector_store: Any,
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
                        success = self.vector_store.delete(memory_id)
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
                        if operation == "add":
                            success = self.vector_store.add(
                                id=memory_id,
                                content=memory["content"],
                                metadata={
                                    "id": memory_id,
                                    "category": memory["category"],
                                    "importance": memory["importance"],
                                    "source": memory["source"],
                                    "created_at": memory["created_at"],
                                },
                            )
                        elif operation == "update":
                            success = self.vector_store.update(
                                id=memory_id,
                                content=memory["content"],
                                metadata={
                                    "id": memory_id,
                                    "category": memory["category"],
                                    "importance": memory["importance"],
                                    "source": memory["source"],
                                    "updated_at": memory["updated_at"],
                                },
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


class VectorStoreAdapter:
    """向量存储适配器.

    提供统一的向量存储接口，支持不同的向量存储后端。
    """

    def __init__(self, workspace: Path, embedding_model: str | None = None) -> None:
        """初始化向量存储适配器.

        Args:
            workspace: 工作目录路径。
            embedding_model: 嵌入模型名称。
        """
        self.workspace = workspace
        self.embedding_model = embedding_model or "BAAI/bge-small-zh-v1.5"
        self.vectorstore = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """确保向量存储已初始化."""
        if not self._initialized:
            self._init_vectorstore()
            self._initialized = True

    def _init_vectorstore(self) -> None:
        """初始化向量存储."""
        try:
            from finchbot.memory.vector import VectorMemoryStore

            self.vectorstore = VectorMemoryStore(self.workspace)

            # 确保嵌入模型可用
            if not self.vectorstore.vectorstore:
                logger.warning("Vector store not available")
                self.vectorstore = None
            else:
                logger.info(f"Vector store initialized with model: {self.embedding_model}")

        except Exception as e:
            logger.warning(f"Vector store init failed: {e}")
            self.vectorstore = None

    def add(self, id: str, content: str, metadata: dict[str, Any]) -> bool:
        """添加记忆到向量存储.

        Args:
            id: 记忆ID。
            content: 记忆内容。
            metadata: 元数据。

        Returns:
            是否成功添加。
        """
        self._ensure_initialized()
        if not self.vectorstore:
            return False

        try:
            success = self.vectorstore.remember(content, metadata, id=id)
            if success:
                logger.debug(f"Added to vector store: {id[:8]}...")
            return success
        except Exception as e:
            logger.error(f"Add to vector store error: {e}")
            return False

    def update(self, id: str, content: str, metadata: dict[str, Any]) -> bool:
        """更新向量存储中的记忆.

        Args:
            id: 记忆ID。
            content: 记忆内容。
            metadata: 元数据。

        Returns:
            是否成功更新。
        """
        self._ensure_initialized()
        if not self.vectorstore:
            return False

        try:
            self.vectorstore.delete(ids=[id])
            success = self.vectorstore.remember(content, metadata, id=id)
            if success:
                logger.debug(f"Updated in vector store: {id[:8]}...")
            return success
        except Exception as e:
            logger.error(f"Update vector store error: {e}")
            return False

    def delete(self, id: str) -> bool:
        """从向量存储删除记忆.

        Args:
            id: 记忆ID。

        Returns:
            是否成功删除。
        """
        self._ensure_initialized()
        if not self.vectorstore:
            return False

        try:
            success = self.vectorstore.delete(ids=[id])
            if success:
                logger.debug(f"Deleted from vector store: {id[:8]}...")
            return success
        except Exception as e:
            logger.error(f"Delete from vector store error: {e}")
            return False

    def get(self, id: str) -> dict[str, Any] | None:
        """从向量存储获取记忆.

        Args:
            id: 记忆ID。

        Returns:
            记忆字典，如果不存在返回None。
        """
        self._ensure_initialized()
        if not self.vectorstore:
            return None

        try:
            return self.vectorstore.get_by_id(id)
        except Exception as e:
            logger.error(f"Get from vector store error: {e}")
            return None

    def get_all_ids(self) -> list[str]:
        """获取向量存储中的所有记忆ID.

        Returns:
            记忆ID列表。
        """
        self._ensure_initialized()
        if not self.vectorstore:
            return []

        try:
            return self.vectorstore.get_all_ids()
        except Exception as e:
            logger.error(f"Get all IDs from vector store error: {e}")
            return []

    def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """在向量存储中搜索.

        Args:
            query: 查询文本。
            top_k: 返回数量。
            similarity_threshold: 相似度阈值。

        Returns:
            搜索结果列表。
        """
        self._ensure_initialized()
        if not self.vectorstore:
            return []

        try:
            # 使用recall方法进行搜索
            return self.vectorstore.recall(
                query=query,
                k=top_k,
                similarity_threshold=similarity_threshold,
            )
        except Exception as e:
            logger.error(f"Search vector store error: {e}")
            return []

    def is_available(self) -> bool:
        """检查向量存储是否可用.

        Returns:
            是否可用。
        """
        self._ensure_initialized()
        return self.vectorstore is not None
