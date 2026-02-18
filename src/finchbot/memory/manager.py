"""记忆管理器.

作为记忆系统的核心业务逻辑层，整合存储层和视图层。
提供统一的记忆管理接口，保持与现有工具的兼容性。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from finchbot.memory.classifier import Classifier
from finchbot.memory.sqlite_store import SQLiteStore
from finchbot.memory.types import RetrievalStrategy
from finchbot.memory.vector_sync import DataSyncManager, VectorStoreAdapter

DEFAULT_MAX_RETRIES = 3
DEFAULT_TOP_K = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.5
DEFAULT_FORGET_LIMIT = 1000
DEFAULT_SEARCH_LIMIT = 100
DEFAULT_RECENT_DAYS = 7
DEFAULT_RECENT_LIMIT = 20
DEFAULT_IMPORTANT_MIN_IMPORTANCE = 0.8
DEFAULT_IMPORTANT_LIMIT = 20
BASE_IMPORTANCE = 0.5
CONTENT_LENGTH_LONG_THRESHOLD = 100
CONTENT_LENGTH_SHORT_THRESHOLD = 20
CONTENT_LENGTH_IMPORTANCE_DELTA = 0.1
KEYWORD_IMPORTANCE_DELTA = 0.2
MIN_IMPORTANCE = 0.1
MAX_IMPORTANCE = 1.0


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

    def __init__(self, workspace: Path) -> None:
        """初始化记忆管理器.

        Args:
            workspace: 工作目录路径。
        """
        self.workspace = workspace
        self.memory_dir = workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 初始化存储层
        self.sqlite_store = SQLiteStore(self.memory_dir / "memory.db")
        self.vector_adapter = VectorStoreAdapter(self.workspace)

        # 简化同步管理器，移除异步队列
        self.sync_manager = DataSyncManager(
            sqlite_store=self.sqlite_store,
            vector_store=self.vector_adapter,
            max_retries=DEFAULT_MAX_RETRIES,
        )

        # 分类器懒加载
        self._classifier = None

        # 后台预加载向量存储（不阻塞主线程）
        self._preload_vector_store()

        logger.info(f"MemoryManager initialized at {self.workspace}")

    def _preload_vector_store(self) -> None:
        """后台预加载向量存储（不阻塞主线程）."""
        import threading

        def preload():
            try:
                # 立即预加载，不延迟
                self.vector_adapter._ensure_initialized()
                logger.debug("Vector store preloaded in background")
            except Exception as e:
                logger.debug(f"Vector store preload failed: {e}")

        thread = threading.Thread(target=preload, daemon=True)
        thread.start()

    @property
    def classifier(self) -> Any:
        """分类器（懒加载）.

        Returns:
            分类器实例。
        """
        if self._classifier is None:
            self._classifier = Classifier(str(self.workspace))
        return self._classifier

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
            importance = self._calculate_importance(content, category)

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

        # 同步到向量存储（直接同步，确保一致性）
        sync_success = self.sync_manager.sync_memory(memory_id, "add")

        if not sync_success and self.vector_adapter.is_available():
            logger.warning(
                f"Memory saved to SQLite but failed to sync to vector store: {memory_id[:8]}..."
            )
        elif not self.vector_adapter.is_available():
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

    def _filter_memory(
        self, memory: dict[str, Any], category: str | None, include_archived: bool
    ) -> bool:
        """过滤记忆条目是否符合条件.

        Args:
            memory: 记忆条目。
            category: 分类过滤。
            include_archived: 是否包含归档的记忆。

        Returns:
            是否符合条件。
        """
        if category and memory["category"] != category:
            return False
        return include_archived or not memory.get("is_archived", False)

    def _fetch_vector_memories(
        self, vector_results: list[dict[str, Any]], category: str | None, include_archived: bool
    ) -> list[dict[str, Any]]:
        """从向量存储结果获取完整记忆信息.

        Args:
            vector_results: 向量搜索结果。
            category: 分类过滤。
            include_archived: 是否包含归档的记忆。

        Returns:
            完整的记忆列表。
        """
        memories = []
        for vec_result in vector_results:
            memory_id = vec_result.get("id")
            if not memory_id:
                continue
            memory = self.sqlite_store.get_memory(memory_id)
            if not memory:
                continue
            if self._filter_memory(memory, category, include_archived):
                memories.append(memory)
        return memories

    def recall(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        category: str | None = None,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """检索记忆.

        Args:
            query: 查询内容。
            top_k: 最大返回数量。
            category: 分类过滤。
            strategy: 检索策略。
            similarity_threshold: 相似度阈值。
            include_archived: 是否包含归档的记忆。

        Returns:
            记忆列表。
        """
        results = []

        # 根据策略选择检索方式
        if strategy == RetrievalStrategy.KEYWORD:
            # 仅使用SQLite关键词检索
            results = self.sqlite_store.search_memories(
                query=query,
                category=category,
                include_archived=include_archived,
                limit=top_k,
            )

        elif strategy == RetrievalStrategy.SEMANTIC and self.vector_adapter.is_available():
            # 仅使用向量语义检索
            vector_results = self.vector_adapter.search(
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
            results = self._fetch_vector_memories(vector_results, category, include_archived)

        elif strategy == RetrievalStrategy.HYBRID:
            # 混合检索：关键词 + 语义
            keyword_results = self.sqlite_store.search_memories(
                query=query,
                category=category,
                include_archived=include_archived,
                limit=top_k,
            )

            vector_results = []
            if self.vector_adapter.is_available():
                vector_results_raw = self.vector_adapter.search(
                    query=query,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                )
                vector_results = self._fetch_vector_memories(
                    vector_results_raw, category, include_archived
                )

            # 合并结果（去重，按重要性排序）
            seen_ids = set()
            combined = []

            for result in keyword_results + vector_results:
                memory_id = result["id"]
                if memory_id not in seen_ids:
                    seen_ids.add(memory_id)
                    combined.append(result)

            # 按重要性排序
            combined.sort(key=lambda x: x["importance"], reverse=True)
            results = combined[:top_k]

        else:
            # 默认使用关键词检索
            results = self.sqlite_store.search_memories(
                query=query,
                category=category,
                include_archived=include_archived,
                limit=top_k,
            )

        # 记录访问日志
        for memory in results:
            self.sqlite_store.record_access(memory["id"], "read", f"recall: {query}")

        logger.debug(f"Recalled {len(results)} memories for query: {query}")
        return results

    def forget(self, pattern: str) -> dict[str, Any]:
        """删除记忆.

        优化版：同步从向量存储删除，确保数据一致性。

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

            # 同步从向量存储删除（直接同步，确保一致性）
            sync_success = self.sync_manager.sync_memory(memory_id, "delete")

            if not sync_success and self.vector_adapter.is_available():
                logger.warning(
                    f"Memory deleted from SQLite but failed to delete from vector store: {memory_id[:8]}..."
                )
            elif not self.vector_adapter.is_available():
                logger.debug(
                    f"Vector store not available, memory deleted from SQLite only: {memory_id[:8]}..."
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
        """获取记忆详情.

        Args:
            memory_id: 记忆ID。

        Returns:
            记忆字典，如果不存在返回None。
        """
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
        """更新记忆.

        优化版：同步更新向量存储，确保数据一致性。

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
        updated = self.sqlite_store.update_memory(
            memory_id=memory_id,
            content=content,
            category=category,
            importance=importance,
            tags=tags,
            metadata=metadata,
        )

        if updated:
            # 同步到向量存储（直接同步，确保一致性）
            sync_success = self.sync_manager.sync_memory(memory_id, "update")

            if not sync_success and self.vector_adapter.is_available():
                logger.warning(
                    f"Memory updated in SQLite but failed to sync to vector store: {memory_id[:8]}..."
                )
            elif not self.vector_adapter.is_available():
                logger.debug(
                    f"Vector store not available, memory updated in SQLite only: {memory_id[:8]}..."
                )

            # 记录访问日志
            self.sqlite_store.record_access(memory_id, "write", "update_memory")

            logger.debug(f"Memory updated: {memory_id[:8]}...")

        return updated

    def archive_memory(self, memory_id: str) -> bool:
        """归档记忆.

        优化版：同步从向量存储删除，确保数据一致性。

        Args:
            memory_id: 记忆ID。

        Returns:
            是否成功归档。
        """
        archived = self.sqlite_store.archive_memory(memory_id)

        if archived:
            # 同步从向量存储删除（归档的记忆不再用于检索）
            sync_success = self.sync_manager.sync_memory(memory_id, "delete")

            if not sync_success and self.vector_adapter.is_available():
                logger.warning(
                    f"Memory archived in SQLite but failed to delete from vector store: {memory_id[:8]}..."
                )
            elif not self.vector_adapter.is_available():
                logger.debug(
                    f"Vector store not available, memory archived in SQLite only: {memory_id[:8]}..."
                )

            logger.debug(f"Memory archived: {memory_id[:8]}...")

        return archived

    def unarchive_memory(self, memory_id: str) -> bool:
        """取消归档记忆.

        优化版：同步到向量存储，确保数据一致性。

        Args:
            memory_id: 记忆ID。

        Returns:
            是否成功取消归档。
        """
        unarchived = self.sqlite_store.unarchive_memory(memory_id)

        if unarchived:
            # 同步到向量存储
            sync_success = self.sync_manager.sync_memory(memory_id, "add")

            if not sync_success and self.vector_adapter.is_available():
                logger.warning(
                    f"Memory unarchived in SQLite but failed to sync to vector store: {memory_id[:8]}..."
                )
            elif not self.vector_adapter.is_available():
                logger.debug(
                    f"Vector store not available, memory unarchived in SQLite only: {memory_id[:8]}..."
                )

            logger.debug(f"Memory unarchived: {memory_id[:8]}...")

        return unarchived

    def _classify_content(self, content: str) -> str:
        """自动分类内容.

        Args:
            content: 待分类的内容。

        Returns:
            分类标签。
        """
        try:
            return self.classifier.classify(content, use_semantic=False)
        except Exception as e:
            logger.warning(f"Classification failed: {e}, using 'general'")
            return "general"

    def _calculate_importance(self, content: str, category: str) -> float:
        """计算重要性评分.

        Args:
            content: 记忆内容。
            category: 分类标签。

        Returns:
            重要性评分 (0-1)。
        """
        base_importance = BASE_IMPORTANCE

        category_importance = {
            "personal": 0.8,
            "contact": 0.9,
            "goal": 0.7,
            "work": 0.6,
            "preference": 0.5,
            "schedule": 0.7,
        }

        if category in category_importance:
            base_importance = category_importance[category]

        content_length = len(content)
        if content_length > CONTENT_LENGTH_LONG_THRESHOLD:
            base_importance = min(base_importance + CONTENT_LENGTH_IMPORTANCE_DELTA, MAX_IMPORTANCE)
        elif content_length < CONTENT_LENGTH_SHORT_THRESHOLD:
            base_importance = max(base_importance - CONTENT_LENGTH_IMPORTANCE_DELTA, MIN_IMPORTANCE)

        important_keywords = ["重要", "关键", "必须", "紧急", "邮箱", "电话", "密码"]
        for keyword in important_keywords:
            if keyword in content:
                base_importance = min(base_importance + KEYWORD_IMPORTANCE_DELTA, MAX_IMPORTANCE)
                break

        return round(base_importance, 2)

    def get_stats(self) -> dict[str, Any]:
        """获取系统统计信息.

        Returns:
            统计字典。
        """
        # SQLite统计
        sqlite_stats = self.sqlite_store.get_memory_stats()

        # 同步统计
        sync_stats = self.sync_manager.get_sync_status()

        # 向量存储可用性
        vector_available = self.vector_adapter.is_available()

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
        """搜索记忆（直接SQLite搜索）.

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
        """获取最近添加的记忆.

        Args:
            days: 最近天数。
            limit: 返回数量限制。

        Returns:
            记忆列表。
        """
        return self.sqlite_store.get_recent_memories(days=days, limit=limit)

    def get_important_memories(
        self,
        min_importance: float = DEFAULT_IMPORTANT_MIN_IMPORTANCE,
        limit: int = DEFAULT_IMPORTANT_LIMIT,
    ) -> list[dict[str, Any]]:
        """获取重要记忆.

        Args:
            min_importance: 最小重要性阈值。
            limit: 返回数量限制。

        Returns:
            记忆列表。
        """
        return self.sqlite_store.get_important_memories(min_importance=min_importance, limit=limit)

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
        return self.sqlite_store.add_category(
            name=name,
            description=description,
            keywords=keywords,
            parent_id=parent_id,
        )

    def get_categories(self) -> list[dict[str, Any]]:
        """获取所有分类.

        Returns:
            分类列表。
        """
        return self.sqlite_store.get_categories()

    def check_consistency(self) -> dict[str, Any]:
        """检查SQLite和向量存储之间的一致性.

        Returns:
            一致性检查结果，包含：
            - sqlite_count: SQLite中的总记录数
            - vector_count: 向量存储中的记录数
            - active_count: 活跃记忆数
            - missing_in_vector: 在SQLite中但不在向量存储中的记录
            - extra_in_vector: 在向量存储中但不在SQLite中的记录
            - archived_in_vector: 已归档但仍在向量存储中的记录
        """
        # 获取SQLite中的所有记忆
        sqlite_memories = self.sqlite_store.search_memories(
            include_archived=True,
            limit=1000,
        )

        # 获取向量存储中的所有ID
        vector_ids = self.vector_adapter.get_all_ids()

        # 构建ID集合以便快速查找
        sqlite_ids = {memory["id"] for memory in sqlite_memories}
        vector_id_set = set(vector_ids)

        # 找出不一致的记录
        missing_in_vector = []
        extra_in_vector = []
        archived_in_vector = []

        # 检查SQLite中的记录是否在向量存储中
        for memory in sqlite_memories:
            memory_id = memory["id"]
            is_archived = memory.get("is_archived", False)

            if memory_id not in vector_id_set:
                missing_in_vector.append(
                    {
                        "id": memory_id,
                        "content": memory["content"],
                        "is_archived": is_archived,
                    }
                )
            elif is_archived:
                # 记录已归档但仍在向量存储中
                archived_in_vector.append(
                    {
                        "id": memory_id,
                        "content": memory["content"],
                    }
                )

        # 检查向量存储中的记录是否在SQLite中
        for vector_id in vector_ids:
            if vector_id not in sqlite_ids:
                extra_in_vector.append(vector_id)

        # 统计活跃记忆
        active_memories = [m for m in sqlite_memories if not m.get("is_archived", False)]

        result = {
            "sqlite_count": len(sqlite_memories),
            "vector_count": len(vector_ids),
            "active_count": len(active_memories),
            "missing_in_vector": missing_in_vector,
            "extra_in_vector": extra_in_vector,
            "archived_in_vector": archived_in_vector,
            "is_consistent": len(missing_in_vector) == 0 and len(extra_in_vector) == 0,
        }

        # 记录检查结果
        if result["is_consistent"]:
            logger.info(
                f"Consistency check passed: SQLite={result['sqlite_count']}, Vector={result['vector_count']}, Active={result['active_count']}"
            )
        else:
            logger.warning(
                f"Consistency check failed: "
                f"SQLite={result['sqlite_count']}, Vector={result['vector_count']}, "
                f"Missing={len(result['missing_in_vector'])}, Extra={len(result['extra_in_vector'])}, "
                f"Archived in vector={len(result['archived_in_vector'])}"
            )

        return result

    def close(self) -> None:
        """关闭记忆管理器."""
        self.sqlite_store.close()
        logger.info("MemoryManager closed")

    def __enter__(self):
        """上下文管理器入口."""
        return self

    def is_ready(self) -> bool:
        """检查系统是否就绪.

        优化版：即使向量存储还在预加载中，也认为系统就绪。
        向量存储不可用时，仍可进行SQLite操作。

        Returns:
            系统是否就绪。
        """
        return self.sqlite_store is not None

    def wait_until_ready(self, timeout: float = 10.0) -> bool:
        """等待系统就绪.

        TODO: 未使用 - 可能用于异步初始化场景。保留以备未来需要。

        优化版：等待向量存储可用，但SQLite始终可用。

        Args:
            timeout: 超时时间（秒）。

        Returns:
            是否在超时前就绪。
        """
        import time

        # SQLite始终可用
        if self.sqlite_store is None:
            return False

        # 如果向量存储已经可用，立即返回
        if self.vector_adapter.is_available():
            return True

        # 等待向量存储可用
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.vector_adapter.is_available():
                return True
            time.sleep(0.1)

        # 超时后，即使向量存储不可用，也认为系统就绪（SQLite可用）
        return True

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口."""
        self.close()
