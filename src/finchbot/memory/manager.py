"""记忆管理器.

作为记忆系统的核心业务逻辑层，整合存储层和视图层。
提供统一的记忆管理接口，保持与现有工具的兼容性。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from finchbot.memory.services.classification import ClassificationService
from finchbot.memory.services.embedding import EmbeddingService
from finchbot.memory.services.importance import ImportanceScorer
from finchbot.memory.services.retrieval import RetrievalService
from finchbot.memory.storage.sqlite import SQLiteStore
from finchbot.memory.storage.vector import VectorMemoryStore
from finchbot.memory.types import QueryType
from finchbot.memory.vector_sync import DataSyncManager

DEFAULT_MAX_RETRIES = 3
DEFAULT_TOP_K = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.5
DEFAULT_FORGET_LIMIT = 1000
DEFAULT_SEARCH_LIMIT = 100
DEFAULT_RECENT_DAYS = 7
DEFAULT_RECENT_LIMIT = 20
DEFAULT_IMPORTANT_MIN_IMPORTANCE = 0.8
DEFAULT_IMPORTANT_LIMIT = 20


class MemoryManager:
    """记忆管理器.

    提供统一的记忆管理功能，包括：
    1. 记忆保存（remember）
    2. 记忆检索（recall）
    3. 记忆删除（forget）
    4. 智能分类
    5. 重要性管理
    6. 数据同步协调
    """

    def __init__(
        self,
        workspace: Path,
        sqlite_store: SQLiteStore | None = None,
        vector_store: VectorMemoryStore | None = None,
        retrieval_service: RetrievalService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """初始化记忆管理器.

        Args:
            workspace: 工作目录路径。
            sqlite_store: 可选的 SQLite 存储实例。
            vector_store: 可选的向量存储实例。
            retrieval_service: 可选的检索服务实例。
            embedding_service: 可选的 Embedding 服务实例。
        """
        self.workspace = workspace
        self.memory_dir = workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 1. 初始化服务层
        self.embedding_service = embedding_service or EmbeddingService()
        self.importance_scorer = ImportanceScorer()

        # 2. 初始化存储层
        self.sqlite_store = sqlite_store or SQLiteStore(self.memory_dir / "memory.db")
        self.vector_store = vector_store or VectorMemoryStore(
            self.workspace, self.embedding_service
        )

        # 3. 初始化分类服务 (依赖 SQLite 和 Embedding)
        self.classification_service = ClassificationService(
            self.sqlite_store, self.embedding_service
        )

        # 4. 初始化检索服务
        self.retrieval_service = retrieval_service or RetrievalService(
            self.sqlite_store, self.vector_store
        )

        # 5. 初始化同步管理器
        self.sync_manager = DataSyncManager(
            sqlite_store=self.sqlite_store,
            vector_store=self.vector_store,
            max_retries=DEFAULT_MAX_RETRIES,
        )

        logger.info(f"MemoryManager initialized at {self.workspace}")

    def remember(
        self,
        content: str,
        category: str | None = None,
        importance: float | None = None,
        source: str = "manual",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """保存记忆.

        优化版：同步写入向量存储，确保数据一致性。
        如果向量存储不可用，仍会保存到SQLite，但会记录警告。

        Args:
            content: 记忆内容。
            category: 分类标签（如果为None则自动分类）。
            importance: 重要性评分（如果为None则自动评分）。
            source: 来源。
            tags: 标签列表。
            metadata: 元数据。

        Returns:
            记忆字典，如果失败返回None。
        """
        # 自动分类（如果未指定）
        if category is None:
            category = self._classify_content(content)

        # 自动重要性评分（如果未指定）
        if importance is None:
            importance = self.importance_scorer.calculate_importance(content, category)

        # 保存到SQLite
        memory_id = self.sqlite_store.remember(
            content=content,
            category=category,
            importance=importance,
            source=source,
            tags=tags,
            metadata=metadata,
        )

        if not memory_id:
            logger.error("Failed to save memory to SQLite")
            return None

        # 同步到向量存储
        sync_success = self.sync_manager.sync_memory(memory_id, "add")

        if not sync_success and self.vector_store and self.vector_store.vectorstore:
            logger.warning(
                f"Memory saved to SQLite but failed to sync to vector store: {memory_id[:8]}..."
            )
        elif not self.vector_store or not self.vector_store.vectorstore:
            logger.debug(
                f"Vector store not available, memory saved to SQLite only: {memory_id[:8]}..."
            )

        # 记录访问日志
        self.sqlite_store.record_access(memory_id, "write", source)

        # 获取完整的记忆信息
        memory = self.sqlite_store.get_memory(memory_id)

        logger.info(
            f"Memory remembered: {memory_id[:8]}... (category: {category}, importance: {importance:.2f})"
        )
        return memory

    def recall(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        category: str | None = None,
        query_type: QueryType = QueryType.COMPLEX,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """检索记忆.

        Args:
            query: 查询内容。
            top_k: 最大返回数量。
            category: 分类过滤。
            query_type: 查询类型。
            similarity_threshold: 相似度阈值。
            include_archived: 是否包含归档的记忆。

        Returns:
            记忆列表。
        """
        results = self.retrieval_service.search(
            query=query,
            query_type=query_type,
            top_k=top_k,
            category=category,
            similarity_threshold=similarity_threshold,
            include_archived=include_archived,
        )

        # 记录访问日志
        for memory in results:
            self.sqlite_store.record_access(memory["id"], "read", f"recall: {query}")

        logger.debug(f"Recalled {len(results)} memories for query: {query} (type: {query_type})")
        return results

    def forget(self, pattern: str) -> dict[str, Any]:
        """删除记忆.

        Args:
            pattern: 删除模式（支持通配符）。

        Returns:
            删除统计信息。
        """
        # 搜索匹配的记忆
        memories = self.sqlite_store.search_memories(
            query=pattern,
            include_archived=True,
            limit=DEFAULT_FORGET_LIMIT,
        )

        deleted_count = 0
        archived_count = 0

        for memory in memories:
            memory_id = memory["id"]

            # 如果是归档的记忆，直接删除
            if memory.get("is_archived", False):
                self.sqlite_store.delete_memory(memory_id)
                deleted_count += 1
            else:
                # 否则先归档
                self.sqlite_store.archive_memory(memory_id)
                archived_count += 1

            # 同步从向量存储删除
            sync_success = self.sync_manager.sync_memory(memory_id, "delete")

            if not sync_success and self.vector_store and self.vector_store.vectorstore:
                logger.warning(
                    f"Memory deleted from SQLite but failed to delete from vector store: {memory_id[:8]}..."
                )

        stats = {
            "total_found": len(memories),
            "deleted": deleted_count,
            "archived": archived_count,
            "pattern": pattern,
        }

        logger.info(f"Forget operation: {stats}")
        return stats

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """获取记忆详情."""
        memory = self.sqlite_store.get_memory(memory_id)

        if memory:
            # 记录访问日志
            self.sqlite_store.record_access(memory_id, "read", "get_memory")

        return memory

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        category: str | None = None,
        importance: float | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """更新记忆."""
        updated = self.sqlite_store.update_memory(
            memory_id=memory_id,
            content=content,
            category=category,
            importance=importance,
            tags=tags,
            metadata=metadata,
        )

        if updated:
            # 同步到向量存储
            sync_success = self.sync_manager.sync_memory(memory_id, "update")

            if not sync_success and self.vector_store and self.vector_store.vectorstore:
                logger.warning(
                    f"Memory updated in SQLite but failed to sync to vector store: {memory_id[:8]}..."
                )

            # 记录访问日志
            self.sqlite_store.record_access(memory_id, "write", "update_memory")

            logger.debug(f"Memory updated: {memory_id[:8]}...")

        return updated

    def archive_memory(self, memory_id: str) -> bool:
        """归档记忆."""
        archived = self.sqlite_store.archive_memory(memory_id)

        if archived:
            # 同步从向量存储删除（归档的记忆不再用于检索）
            sync_success = self.sync_manager.sync_memory(memory_id, "delete")

            if not sync_success and self.vector_store and self.vector_store.vectorstore:
                logger.warning(
                    f"Memory archived in SQLite but failed to delete from vector store: {memory_id[:8]}..."
                )

            logger.debug(f"Memory archived: {memory_id[:8]}...")

        return archived

    def unarchive_memory(self, memory_id: str) -> bool:
        """取消归档记忆."""
        unarchived = self.sqlite_store.unarchive_memory(memory_id)

        if unarchived:
            # 同步到向量存储
            sync_success = self.sync_manager.sync_memory(memory_id, "add")

            if not sync_success and self.vector_store and self.vector_store.vectorstore:
                logger.warning(
                    f"Memory unarchived in SQLite but failed to sync to vector store: {memory_id[:8]}..."
                )

            logger.debug(f"Memory unarchived: {memory_id[:8]}...")

        return unarchived

    def _classify_content(self, content: str) -> str:
        """自动分类内容."""
        try:
            return self.classification_service.classify(content, use_semantic=False)
        except Exception as e:
            logger.warning(f"Classification failed: {e}, using 'general'")
            return "general"

    def get_stats(self) -> dict[str, Any]:
        """获取系统统计信息."""
        # SQLite统计
        sqlite_stats = self.sqlite_store.get_memory_stats()

        # 同步统计
        sync_stats = self.sync_manager.get_sync_status()

        # 向量存储可用性
        vector_available = (
            self.vector_store is not None and self.vector_store.vectorstore is not None
        )

        stats = {
            "sqlite": sqlite_stats,
            "sync": sync_stats,
            "vector_store_available": vector_available,
            "workspace": str(self.workspace),
            "timestamp": datetime.now().isoformat(),
        }

        return stats

    def search_memories(
        self,
        query: str | None = None,
        category: str | None = None,
        min_importance: float = 0.0,
        max_importance: float = 1.0,
        include_archived: bool = False,
        limit: int = DEFAULT_SEARCH_LIMIT,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """搜索记忆（直接SQLite搜索）."""
        return self.sqlite_store.search_memories(
            query=query,
            category=category,
            min_importance=min_importance,
            max_importance=max_importance,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )

    def get_recent_memories(
        self, days: int = DEFAULT_RECENT_DAYS, limit: int = DEFAULT_RECENT_LIMIT
    ) -> list[dict[str, Any]]:
        """获取最近添加的记忆."""
        return self.sqlite_store.get_recent_memories(days=days, limit=limit)

    def get_important_memories(
        self,
        min_importance: float = DEFAULT_IMPORTANT_MIN_IMPORTANCE,
        limit: int = DEFAULT_IMPORTANT_LIMIT,
    ) -> list[dict[str, Any]]:
        """获取重要记忆."""
        return self.sqlite_store.get_important_memories(min_importance=min_importance, limit=limit)

    def add_category(
        self,
        name: str,
        description: str | None = None,
        keywords: list[str] | None = None,
        parent_id: str | None = None,
    ) -> str:
        """添加分类."""
        return self.sqlite_store.add_category(
            name=name,
            description=description,
            keywords=keywords,
            parent_id=parent_id,
        )

    def get_categories(self) -> list[dict[str, Any]]:
        """获取所有分类."""
        return self.sqlite_store.get_categories()

    def close(self) -> None:
        """关闭记忆管理器."""
        self.sqlite_store.close()
        self.sync_manager.stop()
        logger.info("MemoryManager closed")

    def __enter__(self):
        """上下文管理器入口."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口."""
        self.close()

    def is_ready(self) -> bool:
        """检查系统是否就绪."""
        return self.sqlite_store is not None

    def wait_until_ready(self, timeout: float = 10.0) -> bool:
        """等待系统就绪."""
        # SQLite始终可用，所以只要初始化了就返回True
        # 在新架构中，__init__ 是阻塞的（除了 embedding 懒加载可能），所以实例化后就 ready
        return True
