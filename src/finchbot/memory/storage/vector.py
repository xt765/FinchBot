"""向量记忆存储模块.

使用 ChromaDB + FastEmbed 实现语义检索。
FastEmbed 使用 ONNX Runtime，无 PyTorch 依赖，轻量快速。

优化版：延迟加载 embedding 模型，减少初始化时间。
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from langchain_chroma import Chroma

    from finchbot.memory.services.embedding import EmbeddingService


class VectorMemoryStore:
    """向量记忆存储 - 优化版.

    使用 ChromaDB 进行语义检索，支持：
    - 语义相似度检索
    - 元数据过滤
    - 增量更新
    - 延迟加载 embedding 模型

    使用 FastEmbed 本地模型（轻量级，无 PyTorch 依赖）。

    Attributes:
        workspace: 工作目录路径。
        vectorstore: ChromaDB 向量存储。
        embeddings: Embedding 模型。
    """

    def __init__(self, workspace: Path, embedding_service: EmbeddingService) -> None:
        """初始化向量记忆存储.

        Args:
            workspace: 工作目录路径。
            embedding_service: Embedding 服务实例。
        """
        self.workspace = workspace
        self.vector_dir = workspace / "memory_vectors"
        self.vector_dir.mkdir(parents=True, exist_ok=True)

        self._embedding_service = embedding_service
        self._embeddings = None
        self._vectorstore: Chroma | None = None
        self._initialized = False
        self._initializing = False
        self._init_error: str | None = None

        self._start_lazy_init()

    def _ensure_initialized(self, timeout: float = 30.0) -> bool:
        """确保初始化完成（阻塞等待）.

        Args:
            timeout: 最大等待时间（秒）。

        Returns:
            是否初始化成功。
        """
        if self._initialized:
            return True

        if not self._initializing and not self._initialized:
            self._start_lazy_init()

        start = time.time()
        while self._initializing and time.time() - start < timeout:
            time.sleep(0.05)

        return self._initialized

    def _start_lazy_init(self) -> None:
        """启动后台初始化线程."""
        if self._initializing or self._initialized:
            return
        self._initializing = True
        thread = threading.Thread(target=self._lazy_init, daemon=True)
        thread.start()

    def _lazy_init(self) -> None:
        """延迟初始化向量存储."""
        try:
            self._embeddings = self._embedding_service.get_embeddings()
            if not self._embeddings:
                self._init_error = (
                    "No embedding backend available. Install fastembed: uv add fastembed"
                )
                logger.debug(self._init_error)
                return

            self._init_vectorstore()
            if self._vectorstore:
                self._initialized = True
                logger.debug("VectorMemoryStore initialized successfully")
        except Exception as e:
            self._init_error = str(e)
            logger.debug(f"VectorMemoryStore initialization skipped: {e}")
        finally:
            self._initializing = False

    def _init_vectorstore(self) -> None:
        """初始化向量存储.

        使用 ChromaDB 作为后端，FastEmbed 作为 Embedding 模型。
        显式设置距离度量为 L2 (欧几里得距离)，以确保相似度计算公式 (1 - distance/2) 的正确性。
        """
        if not self._embeddings:
            return

        try:
            import chromadb
            from chromadb.config import Settings
            from langchain_chroma import Chroma

            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    settings = Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )

                    client = chromadb.PersistentClient(
                        path=str(self.vector_dir),
                        settings=settings,
                    )

                    client.get_or_create_collection(
                        name="langchain",
                        metadata={"hnsw:space": "l2"},
                    )

                    self._vectorstore = Chroma(
                        client=client,
                        embedding_function=self._embeddings,
                        collection_metadata={"hnsw:space": "l2"},
                    )
                    logger.debug("Vector store initialized with L2 distance metric")
                    return

                except Exception as e:
                    last_error = e
                    logger.debug(f"ChromaDB init attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))

            raise last_error if last_error else Exception("Unknown error")

        except ImportError:
            self._init_error = "langchain-chroma or chromadb not available"
            logger.debug(self._init_error)
            self._vectorstore = None
        except Exception as e:
            self._init_error = str(e)
            logger.debug(f"Vector store init skipped: {e}")
            self._vectorstore = None

    @property
    def vectorstore(self) -> Chroma | None:
        """获取向量存储（懒加载）."""
        self._ensure_initialized()
        return self._vectorstore

    @property
    def embeddings(self):
        """获取 embedding 模型（懒加载）."""
        self._ensure_initialized()
        return self._embeddings

    def remember(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> bool:
        """添加记忆到向量存储.

        将文本内容转换为向量并存储到 ChromaDB 中，同时存储相关的元数据。

        Args:
            content: 记忆的文本内容。
            metadata: 关联的元数据字典（如分类、重要性、时间戳等）。
            id: 可选的唯一记忆ID。如果不提供，ChromaDB 会自动生成 UUID。

        Returns:
            bool: 添加成功返回 True，失败返回 False。
        """
        if not self._ensure_initialized() or self._vectorstore is None:
            return False

        try:
            self._vectorstore.add_texts(
                texts=[content],
                metadatas=[metadata or {}],
                ids=[id] if id else None,
            )
            logger.debug(f"Added memory: {content[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return False

    def recall(
        self,
        query: str,
        k: int = 5,
        filter: dict[str, Any] | None = None,  # noqa: A002
        similarity_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """语义检索记忆.

        根据查询文本的语义相似度检索最相关的记忆。
        支持元数据过滤和相似度阈值过滤。

        相似度计算说明：
        ChromaDB 默认返回 L2 距离 (distance)，范围通常在 [0, 2] 之间（对于归一化向量）。
        我们将其转换为相似度 (similarity) = 1.0 - (distance / 2.0)。
        - distance = 0 -> similarity = 1.0 (完全相同)
        - distance = 2 -> similarity = 0.0 (完全相反)

        Args:
            query: 查询文本。
            k: 最大返回结果数量。
            filter: 元数据过滤条件（ChromaDB where 语法）。例如 {"category": "personal"}。
            similarity_threshold: 相似度阈值 (0.0-1.0)。只返回相似度大于等于此值的记忆。

        Returns:
            list[dict[str, Any]]: 匹配的记忆列表。每个元素包含：
                - id: 记忆ID
                - content: 记忆内容
                - metadata: 元数据
                - similarity: 相似度分数
        """
        if not self._ensure_initialized() or self._vectorstore is None:
            return []

        try:
            # 使用 similarity_search_with_score 获取相似度分数
            # 获取更多候选结果 (k*2) 以便在过滤后仍能尽量满足 k 个结果
            results_with_scores = self._vectorstore.similarity_search_with_score(
                query,
                k=k * 2,
                filter=filter,
            )

            # 过滤低于阈值的结果
            filtered_results = []
            for doc, score in results_with_scores:
                # ChromaDB 返回的距离分数需要转换为相似度分数
                # 距离范围通常是 [0, 2]，其中 0 表示完全相同
                # 转换为相似度：1 - (distance / 2)
                similarity = 1.0 - (score / 2.0)

                if similarity >= similarity_threshold:
                    filtered_results.append(
                        {
                            "id": doc.metadata.get("id"),
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "similarity": similarity,
                        }
                    )

            # 按相似度降序排序（虽然通常已经是排序的）
            filtered_results.sort(key=lambda x: x["similarity"], reverse=True)

            logger.debug(
                f"Vector recall: query='{query}', found {len(results_with_scores)} candidates, "
                f"{len(filtered_results)} above threshold {similarity_threshold}"
            )

            return filtered_results[:k]
        except Exception as e:
            logger.error(f"Failed to recall: {e}")
            return []

    def delete(
        self,
        ids: list[str] | None = None,
        where_filter: dict[str, Any] | None = None,
    ) -> bool:
        """删除记忆.

        从向量存储中删除指定的记忆。可以通过 ID 列表或元数据过滤条件进行删除。

        Args:
            ids: 要删除的记忆 ID 列表。
            where_filter: 元数据过滤条件（ChromaDB where 语法）。

        Returns:
            bool: 删除成功返回 True，失败返回 False。
        """
        if not self._ensure_initialized() or self._vectorstore is None:
            return False

        try:
            if ids:
                self._vectorstore.delete(ids=ids)
            elif where_filter:
                # ChromaDB 使用 where 参数而不是 filter
                self._vectorstore.delete(where=where_filter)
            return True
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            return False

    def get_memory_context(self, query: str | None = None, k: int = 10) -> str:
        """获取记忆上下文.

        Args:
            query: 可选的查询文本（用于语义检索）。
            k: 最大返回数量。

        Returns:
            格式化的记忆上下文。
        """
        if not self._ensure_initialized() or self._vectorstore is None:
            return ""

        try:
            if query:
                results = self.recall(query, k=k)
            else:
                results = self._vectorstore.similarity_search(
                    "",
                    k=k,
                )
                results = [
                    {"content": doc.page_content, "metadata": doc.metadata} for doc in results
                ]

            if not results:
                return ""

            lines = ["## 记忆库"]
            for i, item in enumerate(results, 1):
                content = item["content"]
                metadata = item.get("metadata", {})
                category = metadata.get("category", "general")
                lines.append(f"{i}. [{category}] {content}")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return ""

    def as_retriever(self, **kwargs):
        """返回检索器.

        Args:
            **kwargs: 传递给 as_retriever 的参数。

        Returns:
            检索器实例。
        """
        if not self._ensure_initialized() or self._vectorstore is None:
            raise ValueError("Vector store not initialized")
        return self._vectorstore.as_retriever(**kwargs)

    def get_all_ids(self) -> list[str]:
        """获取向量存储中所有记忆的 ID.

        Returns:
            ID 列表。
        """
        if not self._ensure_initialized() or self._vectorstore is None:
            return []
        try:
            return self._vectorstore.get()["ids"]
        except Exception as e:
            logger.error(f"Failed to get all IDs: {e}")
            return []

    def get_by_id(self, id: str) -> dict[str, Any] | None:
        """通过 ID 获取单个记忆.

        Args:
            id: 记忆 ID。

        Returns:
            记忆字典，如果不存在返回 None。
        """
        if not self._ensure_initialized() or self._vectorstore is None:
            return None
        try:
            result = self._vectorstore.get(ids=[id])
            if result["ids"] and len(result["ids"]) > 0:
                return {
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get by ID {id[:8]}...: {e}")
            return None
