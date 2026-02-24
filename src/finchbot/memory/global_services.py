"""全局服务管理器.

提供单例模式管理 EmbeddingService 和 VectorMemoryStore，
避免每次会话都重新创建实例和加载模型。
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finchbot.memory.services.embedding import EmbeddingService
    from finchbot.memory.storage.vector import VectorMemoryStore


class GlobalServices:
    """全局服务管理器.

    使用类级别的单例模式，确保：
    1. EmbeddingService 只创建一次
    2. VectorMemoryStore 按 workspace 缓存
    3. 线程安全的实例创建
    """

    _lock = threading.Lock()
    _embedding_service: EmbeddingService | None = None
    _vector_stores: dict[str, VectorMemoryStore] = {}
    _initialized = False

    @classmethod
    def get_embedding_service(cls) -> EmbeddingService:
        """获取全局 EmbeddingService 实例.

        Returns:
            EmbeddingService 单例实例。
        """
        if cls._embedding_service is not None:
            return cls._embedding_service

        with cls._lock:
            if cls._embedding_service is None:
                from finchbot.memory.services.embedding import EmbeddingService

                cls._embedding_service = EmbeddingService(verbose=False)
            return cls._embedding_service

    @classmethod
    def get_vector_store(cls, workspace: Path) -> VectorMemoryStore:
        """获取指定 workspace 的 VectorMemoryStore 实例.

        Args:
            workspace: 工作目录路径。

        Returns:
            VectorMemoryStore 实例（按 workspace 缓存）。
        """
        key = str(workspace.resolve())

        if key in cls._vector_stores:
            return cls._vector_stores[key]

        with cls._lock:
            if key not in cls._vector_stores:
                from finchbot.memory.storage.vector import VectorMemoryStore

                cls._vector_stores[key] = VectorMemoryStore(
                    workspace,
                    cls.get_embedding_service(),
                )
            return cls._vector_stores[key]

    @classmethod
    def is_initialized(cls) -> bool:
        """检查全局服务是否已初始化.

        Returns:
            是否已初始化。
        """
        return cls._embedding_service is not None

    @classmethod
    def reset(cls) -> None:
        """重置所有全局服务.

        用于测试或需要强制重新初始化的场景。
        """
        with cls._lock:
            cls._embedding_service = None
            cls._vector_stores.clear()
            cls._initialized = False
