"""向量记忆存储模块.

使用 ChromaDB + FastEmbed 实现语义检索。
FastEmbed 使用 ONNX Runtime，无 PyTorch 依赖，轻量快速。
"""

from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from langchain_chroma import Chroma
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
# 模型缓存目录（项目内）
MODEL_CACHE_DIR = PROJECT_ROOT / ".models" / "fastembed"

# 模块级缓存：避免重复初始化嵌入模型
_embeddings_cache: FastEmbedEmbeddings | None = None


def _check_internet_connection(
    host: str = "huggingface.co", port: int = 443, timeout: int = 3
) -> bool:
    """检查网络连接.

    Args:
        host: 目标主机
        port: 目标端口
        timeout: 超时时间（秒）

    Returns:
        是否有网络连接
    """
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except OSError:
        return False


def _detect_best_mirror() -> tuple[str, str]:
    """检测最佳下载镜像.

    优先检测国内镜像（hf-mirror.com），如果可访问则使用国内镜像。
    否则使用官方源（huggingface.co）。

    Returns:
        (镜像URL, 镜像名称) 元组
    """
    # 检测国内镜像
    try:
        socket.create_connection(("hf-mirror.com", 443), timeout=2)
        return ("https://hf-mirror.com", "国内镜像")
    except OSError:
        pass

    # 检测官方源
    try:
        socket.create_connection(("huggingface.co", 443), timeout=2)
        return ("https://huggingface.co", "官方源")
    except OSError:
        pass

    # 默认使用官方源（可能离线，但会给出正确提示）
    return ("https://huggingface.co", "官方源")


def _check_model_exists(cache_dir: Path | None = None) -> bool:
    """检查模型文件是否存在.

    Args:
        cache_dir: 缓存目录

    Returns:
        模型是否存在
    """
    model_cache = cache_dir or MODEL_CACHE_DIR
    if not model_cache.exists():
        return False
    # 检查是否有模型文件
    return any(model_cache.rglob("model_optimized.onnx"))


def _print_model_status(
    model_exists: bool,
    has_internet: bool,
    cache_dir: Path,
    mirror_url: str | None = None,
) -> None:
    """打印模型状态提示.

    Args:
        model_exists: 模型是否存在
        has_internet: 是否有网络连接
        cache_dir: 缓存目录
        mirror_url: 使用的镜像URL
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    if model_exists:
        # 模型已存在，显示简洁信息
        logger.info(f"✓ 嵌入模型已就绪: {cache_dir}")
        return

    # 模型不存在
    if has_internet:
        # 有网络，会自动下载
        mirror_display = mirror_url or "自动检测"
        console.print(
            Panel(
                f"[yellow]⚠ 嵌入模型未找到[/yellow]\n\n"
                f"模型将在首次使用时自动下载:\n"
                f"• 模型: BAAI/bge-small-zh-v1.5\n"
                f"• 源: {mirror_display}\n"
                f"• 大小: 约 50MB\n\n"
                f"或手动下载: [cyan]finchbot download-models[/cyan]",
                title="模型状态",
                border_style="yellow",
            )
        )
    else:
        # 无网络，离线模式
        console.print(
            Panel(
                "[red]✗ 嵌入模型未找到且无法连接网络[/red]\n\n"
                "当前处于离线模式，无法下载模型。\n\n"
                "解决方案:\n"
                "1. 连接网络后运行: [cyan]finchbot download-models[/cyan]\n"
                "2. 或从其他机器复制模型到:\n"
                f"   [dim]{cache_dir}[/dim]\n\n"
                "注意: 离线模式下语义记忆功能将不可用",
                title="离线模式",
                border_style="red",
            )
        )


def get_embeddings(cache_dir: Path | None = None, verbose: bool = True):
    """获取 FastEmbed 本地模型.

    FastEmbed 使用 ONNX Runtime，无 PyTorch 依赖，轻量快速。
    支持多语言模型，适合中文。
    模型默认下载到项目 .models 目录，方便打包分发。

    自动检测网络环境，国内用户使用 hf-mirror.com 镜像，国外用户使用官方源。

    Args:
        cache_dir: 可选的自定义缓存目录。
        verbose: 是否显示状态提示。

    Returns:
        FastEmbedEmbeddings 实例或 None。
    """
    global _embeddings_cache

    # 返回缓存的实例（如果已初始化）
    if _embeddings_cache is not None:
        return _embeddings_cache

    # 确定缓存目录
    model_cache = cache_dir or MODEL_CACHE_DIR
    model_cache.mkdir(parents=True, exist_ok=True)

    # 检查模型状态和网络
    model_exists = _check_model_exists(model_cache)
    has_internet = _check_internet_connection()

    # 检测最佳镜像（如果用户未手动设置）
    mirror_url, mirror_name = _detect_best_mirror()
    if "HF_ENDPOINT" not in os.environ:
        os.environ["HF_ENDPOINT"] = mirror_url
        logger.debug(f"Auto-selected mirror: {mirror_name} ({mirror_url})")

    if verbose:
        _print_model_status(model_exists, has_internet, model_cache, mirror_url)

    try:
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        logger.debug(f"Using FastEmbed embeddings (cache: {model_cache}, mirror: {mirror_name})")

        # 尝试初始化 embeddings
        embeddings = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            max_length=512,
            cache_dir=str(model_cache),
        )

        # 缓存实例
        _embeddings_cache = embeddings

        # 如果模型之前不存在，说明是刚下载的，显示成功信息
        if verbose and not model_exists:
            from rich.console import Console

            console = Console()
            console.print("[green]✓ 嵌入模型加载成功[/green]")

        return embeddings

    except ImportError:
        logger.warning("FastEmbed not available. Install with: pip install fastembed")
        return None
    except Exception as e:
        # 详细的错误提示
        error_msg = str(e)

        if not model_exists and not has_internet:
            # 离线模式且模型不存在
            logger.error(
                "无法加载嵌入模型: 处于离线模式且模型未下载\n"
                "请连接网络后运行: finchbot download-models"
            )
        elif "download" in error_msg.lower() or "connection" in error_msg.lower():
            # 下载失败
            logger.error(f"模型下载失败: {e}\n请检查网络连接或手动下载: finchbot download-models")
        else:
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
        id: str | None = None,
    ) -> bool:
        """添加记忆到向量存储.

        Args:
            content: 记忆内容。
            metadata: 元数据（分类、重要性等）。
            id: 可选的记忆ID，如果不提供则自动生成。

        Returns:
            是否成功添加。
        """
        if not self.vectorstore:
            return False

        try:
            self.vectorstore.add_texts(
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
                            "id": doc.metadata.get("id"),
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

        TODO: 未使用 - 可用于生成对话上下文，考虑在记忆工具中集成。

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

        TODO: 未使用 - 为LangChain集成预留，有扩展价值，保留以备未来集成需求。

        Args:
            **kwargs: 传递给 as_retriever 的参数。

        Returns:
            检索器实例。
        """
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        return self.vectorstore.as_retriever(**kwargs)

    def get_all_ids(self) -> list[str]:
        """获取向量存储中所有记忆的 ID.

        Returns:
            ID 列表。
        """
        if not self.vectorstore:
            return []
        try:
            return self.vectorstore.get()["ids"]
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
        if not self.vectorstore:
            return None
        try:
            result = self.vectorstore.get(ids=[id])
            if result["ids"] and len(result["ids"]) > 0:
                return {
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get by ID {id[:8]}...: {e}")
            return None
