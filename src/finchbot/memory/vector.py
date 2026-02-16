"""向量记忆存储模块.

使用 ChromaDB + FastEmbed 实现语义检索。
FastEmbed 使用 ONNX Runtime，无 PyTorch 依赖，轻量快速。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from langchain_chroma import Chroma

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
# 模型缓存目录（项目内）
MODEL_CACHE_DIR = PROJECT_ROOT / ".models" / "fastembed"


def get_embeddings(cache_dir: Path | None = None):
    """获取 FastEmbed 本地模型.

    FastEmbed 使用 ONNX Runtime，无 PyTorch 依赖，轻量快速。
    支持多语言模型，适合中文。
    模型默认下载到项目 .models 目录，方便打包分发。

    Args:
        cache_dir: 可选的自定义缓存目录。

    Returns:
        FastEmbedEmbeddings 实例或 None。
    """
    try:
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        # 设置 HuggingFace 镜像（国内加速）
        if "HF_ENDPOINT" not in os.environ:
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

        # 使用项目内的模型缓存目录
        model_cache = cache_dir or MODEL_CACHE_DIR
        model_cache.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Using FastEmbed embeddings (cache: {model_cache})")
        return FastEmbedEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            max_length=512,
            cache_dir=str(model_cache),
        )
    except ImportError:
        logger.warning("FastEmbed not available. Install with: pip install fastembed")
        return None
    except Exception as e:
        logger.warning(f"FastEmbed embeddings failed: {e}")
        return None


class VectorMemoryStore:
    """向量记忆存储.

    使用 ChromaDB 进行语义检索，支持：
    - 语义相似度检索
    - 元数据过滤
    - 增量更新

    使用 FastEmbed 本地模型（轻量级，无 PyTorch 依赖）。

    Attributes:
        workspace: 工作目录路径。
        vectorstore: ChromaDB 向量存储。
        embeddings: Embedding 模型。
    """

    def __init__(self, workspace: Path) -> None:
        """初始化向量记忆存储.

        Args:
            workspace: 工作目录路径。
        """
        self.workspace = workspace
        self.vector_dir = workspace / "memory_vectors"
        self.vector_dir.mkdir(parents=True, exist_ok=True)

        self.embeddings = get_embeddings()
        if not self.embeddings:
            logger.warning(
                "No embedding backend available. Install fastembed: pip install fastembed"
            )
            self.vectorstore = None
            return

        self.vectorstore: Chroma | None = None
        self._init_vectorstore()

    def _init_vectorstore(self) -> None:
        """初始化向量存储."""
        if not self.embeddings:
            return

        try:
            from langchain_chroma import Chroma

            self.vectorstore = Chroma(
                persist_directory=str(self.vector_dir),
                embedding_function=self.embeddings,
            )
            logger.debug("Vector store initialized")
        except ImportError:
            logger.warning(
                "langchain-chroma not available. Install with: pip install langchain-chroma"
            )
            self.vectorstore = None
        except Exception as e:
            logger.warning(f"Failed to init vector store: {e}")
            self.vectorstore = None

    def remember(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """添加记忆到向量存储.

        Args:
            content: 记忆内容。
            metadata: 元数据（分类、重要性等）。

        Returns:
            是否成功添加。
        """
        if not self.vectorstore:
            return False

        try:
            self.vectorstore.add_texts(
                texts=[content],
                metadatas=[metadata or {}],
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
        filter: dict[str, Any] | None = None,
        similarity_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """语义检索记忆.

        支持相似度阈值过滤，只返回相似度高于阈值的结果。

        Args:
            query: 查询文本。
            k: 返回数量。
            filter: 元数据过滤条件。
            similarity_threshold: 相似度阈值 (0.0-1.0)，默认 0.5。

        Returns:
            匹配的记忆列表，包含相似度分数。
        """
        if not self.vectorstore:
            return []

        try:
            # 使用 similarity_search_with_score 获取相似度分数
            results_with_scores = self.vectorstore.similarity_search_with_score(
                query,
                k=k * 2,  # 获取更多候选结果用于过滤
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
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "similarity": similarity,
                        }
                    )

            logger.debug(
                f"Vector recall: found {len(results_with_scores)} candidates, "
                f"{len(filtered_results)} above threshold {similarity_threshold}"
            )

            return filtered_results[:k]
        except Exception as e:
            logger.error(f"Failed to recall: {e}")
            return []

    def delete(
        self,
        ids: list[str] | None = None,
        filter: dict[str, Any] | None = None,
    ) -> bool:
        """删除记忆.

        Args:
            ids: 要删除的 ID 列表。
            filter: 元数据过滤条件。

        Returns:
            是否成功删除。
        """
        if not self.vectorstore:
            return False

        try:
            if ids:
                self.vectorstore.delete(ids=ids)
            elif filter:
                # ChromaDB 使用 where 参数而不是 filter
                self.vectorstore.delete(where=filter)
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
        if not self.vectorstore:
            return ""

        try:
            if query:
                results = self.recall(query, k=k)
            else:
                results = self.vectorstore.similarity_search(
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
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        return self.vectorstore.as_retriever(**kwargs)
