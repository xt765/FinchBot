"""分类服务.

提供基于 SQLite 数据的混合分类功能：
1. 关键词快速匹配
2. 向量语义分类
3. 自动从 SQLite 加载和缓存分类配置

优化版：延迟加载 embedding 缓存，减少初始化时间。
"""

import json
import threading
from typing import Any

from loguru import logger

from finchbot.i18n import t
from finchbot.memory.services.embedding import EmbeddingService
from finchbot.memory.storage.sqlite import SQLiteStore


class ClassificationService:
    """分类服务 - 优化版.

    特性：
    1. 延迟加载 embedding 缓存（后台线程）
    2. 优先使用关键词匹配（无需 embedding）
    3. 缓存刷新异步执行
    """

    def __init__(
        self,
        sqlite_store: SQLiteStore,
        embedding_service: EmbeddingService,
    ) -> None:
        """初始化分类服务.

        Args:
            sqlite_store: SQLite 存储实例。
            embedding_service: Embedding 服务实例。
        """
        self.sqlite_store = sqlite_store
        self.embedding_service = embedding_service

        # 缓存
        self._categories: dict[str, dict[str, Any]] = {}
        self._category_embeddings: dict[str, list[float]] = {}
        self._cache_loading = False
        self._cache_loaded = False

        # 初始化：确保有默认分类（快速，不依赖 embedding）
        self._ensure_default_categories()
        self._load_categories_sync()

        # 后台异步刷新 embedding 缓存
        self._start_cache_refresh()

    def _load_categories_sync(self) -> None:
        """同步加载分类列表（不含 embedding）."""
        try:
            categories_list = self.sqlite_store.get_categories()
            self._categories = {c["id"]: c for c in categories_list}
            logger.debug(f"Categories loaded: {len(self._categories)}")
        except Exception as e:
            logger.error(f"Failed to load categories: {e}")

    def _start_cache_refresh(self) -> None:
        """启动后台缓存刷新线程."""
        thread = threading.Thread(target=self._refresh_cache_async, daemon=True)
        thread.start()

    def _refresh_cache_async(self) -> None:
        """异步刷新 embedding 缓存."""
        if self._cache_loading:
            return

        self._cache_loading = True
        try:
            embeddings = self.embedding_service.get_embeddings()

            if not embeddings:
                logger.debug("Embedding service not available, skipping semantic cache")
                return

            new_embeddings = {}
            for category_id, info in self._categories.items():
                description = info.get("description")
                if description:
                    try:
                        embedding = embeddings.embed_query(description)
                        new_embeddings[category_id] = embedding
                    except Exception as e:
                        logger.debug(f"Failed to embed category {category_id}: {e}")

            self._category_embeddings = new_embeddings
            self._cache_loaded = True
            logger.debug(f"Classification cache refreshed: {len(new_embeddings)} embeddings")

        except Exception as e:
            logger.debug(f"Failed to refresh classification cache: {e}")
        finally:
            self._cache_loading = False

    def classify(self, text: str, use_semantic: bool = True) -> str:
        """分类文本.

        Args:
            text: 待分类的文本。
            use_semantic: 是否使用语义分类（如果可用）。

        Returns:
            分类标签。
        """
        # 1. 关键词快速匹配 (L1) - 无需 embedding，总是可用
        text_lower = text.lower()

        for category_id, info in self._categories.items():
            keywords = info.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    logger.debug(f"Keyword match: '{keyword}' -> {category_id}")
                    return category_id

        # 2. 向量语义分类 (L2) - 需要缓存加载完成
        if use_semantic and self._cache_loaded and self._category_embeddings:
            return self._classify_by_embedding(text)

        # 3. 默认分类
        return "general"

    def refresh_cache(self) -> None:
        """刷新分类缓存（同步接口，供外部调用）."""
        # 重新加载分类列表
        self._load_categories_sync()
        # 异步刷新 embedding
        self._start_cache_refresh()

    def _classify_by_embedding(self, text: str) -> str:
        """通过向量相似度分类."""
        try:
            embeddings = self.embedding_service.get_embeddings()
            if not embeddings:
                return "general"

            # 计算文本嵌入
            text_embedding = embeddings.embed_query(text)

            # 计算与每个分类描述的相似度
            best_category = "general"
            best_similarity = 0.0

            for category_id, category_embedding in self._category_embeddings.items():
                similarity = self._cosine_similarity(text_embedding, category_embedding)

                # 阈值判定
                if similarity > best_similarity and similarity > 0.5:
                    best_similarity = similarity
                    best_category = category_id

            if best_category != "general":
                logger.debug(f"Semantic match: {best_category} (score: {best_similarity:.2f})")

            return best_category

        except Exception as e:
            logger.warning(f"Semantic classification failed: {e}")
            return "general"

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _ensure_default_categories(self) -> None:
        """确保数据库中存在默认分类."""
        # 定义默认分类ID
        category_ids = [
            "personal",
            "preference",
            "work",
            "contact",
            "goal",
            "schedule",
            "general",
        ]

        try:
            # 检查是否已有分类
            existing = self.sqlite_store.get_categories()
            if existing:
                return

            logger.info("Seeding default categories...")

            for cat_id in category_ids:
                # 从 i18n 获取配置
                name_key = f"memory.categories.{cat_id}.name"
                desc_key = f"memory.categories.{cat_id}.description"
                keywords_key = f"memory.categories.{cat_id}.keywords"

                name = t(name_key)
                desc = t(desc_key)
                keywords = t(keywords_key)

                # Fallback logic if t() returns the key itself (meaning missing)
                # Note: Assuming t() behavior is returning key string if not found
                if str(name) == name_key:
                    name = cat_id.title()

                if str(desc) == desc_key:
                    desc = f"{cat_id} category"

                if str(keywords) == keywords_key or not isinstance(keywords, list):
                    keywords = []

                info = {
                    "name": name,
                    "description": desc,
                    "keywords": keywords,
                }

                self._seed_category(cat_id, info)

        except Exception as e:
            logger.error(f"Failed to ensure default categories: {e}")

    def _seed_category(self, cat_id: str, info: dict[str, Any]) -> None:
        """直接插入分类（绕过 UUID 生成）."""
        with self.sqlite_store._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO categories (id, name, description, keywords, parent_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cat_id, info["name"], info["description"], json.dumps(info["keywords"]), None),
            )
