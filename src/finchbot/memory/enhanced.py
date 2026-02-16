"""增强记忆系统.

提供智能记忆提取、重要性评分和语义检索功能。
采用 Agentic RAG 方案：Agent 通过工具调用决定何时检索。

支持三种检索策略：
1. SEMANTIC (语义): 仅使用向量语义检索
2. KEYWORD (关键词): 仅使用关键词文本匹配
3. HYBRID (混合): 向量 + 关键词检索，RRF 融合结果

分类采用混合方案：关键词快速匹配 + 向量语义确认。

性能优化特性：
- L0: 查询结果缓存
- L1: 精确查询快速路径
- 性能统计追踪
"""

import hashlib
import math
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from finchbot.memory.types import RetrievalStrategy


@dataclass
class MemoryEntry:
    """记忆条目.

    Attributes:
        content: 记忆内容。
        importance: 重要性评分 (0-1)。
        category: 分类标签。
        created_at: 创建时间。
        source: 来源（会话 ID 或手动添加）。
    """

    content: str
    importance: float = 0.5
    category: str = "general"
    created_at: datetime = field(default_factory=datetime.now)
    source: str = "manual"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "content": self.content,
            "importance": self.importance,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """从字典创建实例."""
        return cls(
            content=data["content"],
            importance=data.get("importance", 0.5),
            category=data.get("category", "general"),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(),
            source=data.get("source", "manual"),
        )


class EnhancedMemoryStore:
    """增强记忆存储.

    采用 Agentic RAG 方案：
    - Agent 通过 remember/recall 工具主动管理记忆
    - 支持向量语义检索（可选）或简单文本匹配
    - JSON 文件持久化
    - 混合分类：关键词快速匹配 + 向量语义确认

    性能优化：
    - L0: 查询结果缓存（LRU，100 条）
    - L1: 精确查询快速路径
    - 性能统计追踪

    Attributes:
        workspace: 工作目录路径。
        vectorstore: 向量存储（可选）。
        category_keywords: 分类关键词（从 i18n 加载）。
        category_descriptions: 分类描述（用于向量语义分类）。
    """

    EXACT_QUERY_KEYWORDS = frozenset({"邮箱", "电话", "生日", "名字", "年龄", "地址", "微信", "QQ", "手机", "账号"})

    MAX_CACHE_SIZE = 100

    def __init__(self, workspace: Path, lang: str | None = None) -> None:
        """初始化增强记忆存储.

        Args:
            workspace: 工作目录路径。
            lang: 语言代码，如果为 None 则自动检测。
        """
        self.workspace = workspace
        self.memory_dir = workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.entries_file = self.memory_dir / "entries.json"
        self._entries: list[MemoryEntry] = []
        self._vectorstore: Any = None
        self._embeddings: Any = None
        self._category_embeddings: dict[str, list[float]] | None = None

        self.lang = lang or self._detect_language()
        self.category_keywords: dict[str, list[str]] = {}
        self.category_descriptions: dict[str, str] = {}

        self._query_cache: OrderedDict[str, list[MemoryEntry]] = OrderedDict()
        self._stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "exact_hits": 0,
            "keyword_hits": 0,
            "vector_hits": 0,
            "total_response_time_ms": 0.0,
        }

        self._load_category_config()
        self._load_entries()
        self._init_vectorstore()

    def _detect_language(self) -> str:
        """检测当前语言."""
        try:
            from finchbot.i18n import get_i18n

            return get_i18n().language
        except Exception:
            return "zh-CN"

    def _load_category_config(self) -> None:
        """从 i18n 配置加载分类关键词和描述."""
        categories = ["personal", "preference", "work", "contact", "goal", "schedule"]

        try:
            from finchbot.i18n import get_i18n

            i18n = get_i18n()

            for cat in categories:
                keywords = i18n.get_raw(f"memory.categories.{cat}.keywords", [])
                if keywords:
                    if isinstance(keywords, list):
                        self.category_keywords[cat] = keywords
                    elif isinstance(keywords, str):
                        self.category_keywords[cat] = [keywords]

                description = i18n.get_raw(f"memory.categories.{cat}.description", "")
                if description:
                    self.category_descriptions[cat] = description

            logger.debug(
                f"Loaded category config from i18n: {len(self.category_keywords)} categories"
            )
        except Exception as e:
            logger.warning(f"Failed to load category config from i18n: {e}")

        if not self.category_keywords:
            logger.warning("No category keywords loaded, classification will default to 'general'")

    def _init_vectorstore(self) -> None:
        """初始化向量存储（可选）."""
        try:
            from finchbot.memory.vector import VectorMemoryStore, get_embeddings

            self._vectorstore = VectorMemoryStore(self.workspace)
            self._embeddings = get_embeddings()

            if not self._vectorstore.vectorstore:
                self._vectorstore = None
                logger.debug("Vector store not available, using text matching")
        except Exception as e:
            logger.debug(f"Vector store init failed: {e}")
            self._vectorstore = None
            self._embeddings = None

    def _generate_cache_key(
        self,
        query: str,
        category: str | None,
        strategy: RetrievalStrategy,
        top_k: int,
    ) -> str:
        """生成查询缓存键.

        Args:
            query: 查询文本。
            category: 分类过滤。
            strategy: 检索策略。
            top_k: 返回数量。

        Returns:
            MD5 缓存键。
        """
        key_str = f"{query}|{category or ''}|{strategy.value}|{top_k}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> list[MemoryEntry] | None:
        """从缓存获取结果.

        Args:
            cache_key: 缓存键。

        Returns:
            缓存的记忆条目列表，如果未命中返回 None。
        """
        if cache_key in self._query_cache:
            self._query_cache.move_to_end(cache_key)
            return self._query_cache[cache_key]
        return None

    def _update_cache(self, cache_key: str, results: list[MemoryEntry]) -> None:
        """更新查询缓存.

        Args:
            cache_key: 缓存键。
            results: 记忆条目列表。
        """
        self._query_cache[cache_key] = results[:5]
        self._query_cache.move_to_end(cache_key)
        if len(self._query_cache) > self.MAX_CACHE_SIZE:
            self._query_cache.popitem(last=False)

    def _is_exact_query(self, query: str) -> bool:
        """判断是否为精确查询.

        Args:
            query: 查询文本。

        Returns:
            是否为精确查询。
        """
        return any(keyword in query for keyword in self.EXACT_QUERY_KEYWORDS)

    def _exact_match(self, query: str, category: str | None) -> list[MemoryEntry]:
        """精确匹配检索.

        Args:
            query: 查询文本。
            category: 分类过滤。

        Returns:
            匹配的记忆条目列表。
        """
        results = []
        query_lower = query.lower()
        for entry in self._entries:
            if category and entry.category != category:
                continue
            if query_lower in entry.content.lower():
                results.append(entry)
        results.sort(key=lambda x: x.importance, reverse=True)
        return results

    def _update_stats(
        self,
        response_time_ms: float,
        cache_hit: bool = False,
        exact_hit: bool = False,
        keyword_hit: bool = False,
        vector_hit: bool = False,
    ) -> None:
        """更新性能统计.

        Args:
            response_time_ms: 响应时间（毫秒）。
            cache_hit: 是否命中缓存。
            exact_hit: 是否命中精确匹配。
            keyword_hit: 是否命中关键词匹配。
            vector_hit: 是否使用了向量检索。
        """
        self._stats["total_queries"] += 1
        if cache_hit:
            self._stats["cache_hits"] += 1
        if exact_hit:
            self._stats["exact_hits"] += 1
        if keyword_hit:
            self._stats["keyword_hits"] += 1
        if vector_hit:
            self._stats["vector_hits"] += 1
        self._stats["total_response_time_ms"] += response_time_ms

    def get_stats(self) -> dict[str, Any]:
        """获取性能统计.

        Returns:
            性能统计字典。
        """
        stats = self._stats.copy()
        total = stats["total_queries"]
        if total > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / total
            stats["exact_hit_rate"] = stats["exact_hits"] / total
            stats["keyword_hit_rate"] = stats["keyword_hits"] / total
            stats["vector_hit_rate"] = stats["vector_hits"] / total
            stats["avg_response_time_ms"] = stats["total_response_time_ms"] / total
        else:
            stats["cache_hit_rate"] = 0.0
            stats["exact_hit_rate"] = 0.0
            stats["keyword_hit_rate"] = 0.0
            stats["vector_hit_rate"] = 0.0
            stats["avg_response_time_ms"] = 0.0
        stats["cache_size"] = len(self._query_cache)
        stats["total_memories"] = len(self._entries)
        return stats

    def get_cache_size(self) -> int:
        """获取缓存大小.

        Returns:
            当前缓存条目数。
        """
        return len(self._query_cache)

    def clear_cache(self) -> None:
        """清空查询缓存."""
        self._query_cache.clear()
        logger.info("Query cache cleared")

    def _load_entries(self) -> None:
        """从文件加载记忆条目."""
        import json

        if self.entries_file.exists():
            try:
                content = self.entries_file.read_text(encoding="utf-8").strip()
                if not content:
                    self._entries = []
                    return
                data = json.loads(content)
                self._entries = [MemoryEntry.from_dict(e) for e in data]
            except Exception as e:
                logger.warning(f"Failed to load memory entries: {e}")
                self._entries = []

    def _save_entries(self) -> None:
        """保存记忆条目到文件."""
        import json

        try:
            data = [e.to_dict() for e in self._entries]
            with open(self.entries_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory entries: {e}")

    def _determine_category(self, text: str) -> str:
        """混合分类：关键词快速匹配 + 向量语义确认.

        Args:
            text: 待分类的文本。

        Returns:
            分类标签。
        """
        # 1. 关键词快速匹配
        text_lower = text.lower()
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return category

        # 2. 向量语义分类（兜底）
        return self._classify_by_embedding(text)

    def _classify_by_embedding(self, text: str) -> str:
        """通过向量相似度分类.

        Args:
            text: 待分类的文本。

        Returns:
            分类标签。
        """
        if not self._embeddings or not self.category_descriptions:
            return "general"

        try:
            # 懒加载分类描述嵌入
            if self._category_embeddings is None:
                self._cache_category_embeddings()

            if not self._category_embeddings:
                return "general"

            # 计算文本嵌入
            text_embedding = self._embeddings.embed_query(text)

            # 计算相似度
            best_category = "general"
            best_score = 0.5  # 阈值

            for cat, desc_embedding in self._category_embeddings.items():
                score = self._cosine_similarity(text_embedding, desc_embedding)
                if score > best_score:
                    best_score = score
                    best_category = cat

            logger.debug(
                f"Classified by embedding: '{text[:30]}...' -> {best_category} ({best_score:.2f})"
            )
            return best_category
        except Exception as e:
            logger.debug(f"Embedding classification failed: {e}")
            return "general"

    def _cache_category_embeddings(self) -> None:
        """缓存分类描述的嵌入向量."""
        if not self._embeddings or not self.category_descriptions:
            return

        try:
            self._category_embeddings = {}
            for cat, description in self.category_descriptions.items():
                self._category_embeddings[cat] = self._embeddings.embed_query(description)
            logger.debug(f"Cached embeddings for {len(self._category_embeddings)} categories")
        except Exception as e:
            logger.debug(f"Failed to cache category embeddings: {e}")
            self._category_embeddings = None

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """计算余弦相似度.

        Args:
            a: 向量 a。
            b: 向量 b。

        Returns:
            余弦相似度 (0-1)。
        """
        dot_product = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _calculate_importance(self, text: str, explicit_score: float | None = None) -> float:
        """计算记忆重要性评分."""
        base_score = 0.5

        importance_boosters = [
            ("重要", 0.25),
            ("关键", 0.25),
            ("必须", 0.2),
            ("紧急", 0.25),
            ("别忘了", 0.15),
            ("记住", 0.1),
        ]

        for indicator, boost in importance_boosters:
            if indicator in text:
                base_score += boost

        category_scores = {
            "personal": 0.15,
            "contact": 0.2,
            "goal": 0.15,
            "schedule": 0.1,
            "preference": 0.05,
            "work": 0.1,
        }

        category = self._determine_category(text)
        if category in category_scores:
            base_score += category_scores[category]

        info_patterns = [
            (r"我(叫|是)\w+", 0.1),
            (r"(电话|邮箱|微信|联系方式)", 0.15),
            (r"(生日|年龄|住址)", 0.1),
            (r"(喜欢|讨厌|偏好)", 0.05),
            (r"(目标|计划|梦想)", 0.1),
        ]

        for pattern, boost in info_patterns:
            if re.search(pattern, text):
                base_score += boost

        final_score = min(1.0, base_score)

        if explicit_score is not None:
            final_score = (final_score + explicit_score) / 2

        return round(final_score, 2)

    def _find_duplicate(self, content: str) -> MemoryEntry | None:
        """查找重复的记忆条目.

        Args:
            content: 要检查的内容。

        Returns:
            如果找到重复条目则返回，否则返回 None。
        """
        content_normalized = content.strip().lower()
        for entry in self._entries:
            if entry.content.strip().lower() == content_normalized:
                return entry
        return None

    def remember(
        self,
        content: str,
        importance: float | None = None,
        category: str | None = None,
        source: str = "manual",
    ) -> MemoryEntry:
        """添加新记忆.

        如果内容已存在，则更新现有条目。

        Args:
            content: 记忆内容。
            importance: 可选的重要性评分。
            category: 可选的分类标签。
            source: 来源标识。

        Returns:
            创建或更新的记忆条目。
        """
        # 检查重复
        existing = self._find_duplicate(content)
        if existing:
            # 更新现有条目
            existing.importance = max(
                existing.importance, self._calculate_importance(content, importance)
            )
            existing.category = category or existing.category
            existing.source = source
            self._save_entries()
            logger.info(
                f"Memory updated: {content[:50]}... (importance: {existing.importance:.2f})"
            )
            return existing

        # 创建新条目
        entry = MemoryEntry(
            content=content,
            importance=self._calculate_importance(content, importance),
            category=category or self._determine_category(content),
            source=source,
        )

        self._entries.append(entry)
        self._save_entries()

        if self._vectorstore:
            try:
                self._vectorstore.remember(
                    content,
                    metadata={
                        "importance": entry.importance,
                        "category": entry.category,
                        "source": entry.source,
                    },
                )
            except Exception as e:
                logger.debug(f"Failed to add to vector store: {e}")

        logger.info(f"New memory added: {content[:50]}... (importance: {entry.importance:.2f})")
        return entry

    def _reciprocal_rank_fusion(
        self,
        semantic_results: list[tuple[MemoryEntry, float]],
        keyword_results: list[tuple[MemoryEntry, float]],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        k: int = 60,
    ) -> list[MemoryEntry]:
        """RRF (Reciprocal Rank Fusion) 算法融合检索结果.

        将向量语义检索和关键词检索的结果进行融合排序。

        Args:
            semantic_results: 向量检索结果列表，每项为 (entry, score)。
            keyword_results: 关键词检索结果列表，每项为 (entry, score)。
            semantic_weight: 向量检索结果权重。
            keyword_weight: 关键词检索结果权重。
            k: RRF 常数，用于平滑排名分数。

        Returns:
            融合后的记忆条目列表。
        """
        # 使用内容作为唯一标识
        scores: dict[str, tuple[float, MemoryEntry]] = {}

        # 处理向量检索结果
        for rank, (entry, _) in enumerate(semantic_results):
            content_key = entry.content.strip().lower()
            rrf_score = semantic_weight * (1.0 / (k + rank + 1))
            if content_key in scores:
                scores[content_key] = (scores[content_key][0] + rrf_score, entry)
            else:
                scores[content_key] = (rrf_score, entry)

        # 处理关键词检索结果
        for rank, (entry, _) in enumerate(keyword_results):
            content_key = entry.content.strip().lower()
            rrf_score = keyword_weight * (1.0 / (k + rank + 1))
            if content_key in scores:
                scores[content_key] = (scores[content_key][0] + rrf_score, entry)
            else:
                scores[content_key] = (rrf_score, entry)

        # 按 RRF 分数排序
        sorted_results = sorted(scores.values(), key=lambda x: x[0], reverse=True)
        return [entry for _, entry in sorted_results]

    def recall(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_importance: float = 0.0,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        similarity_threshold: float = 0.5,
        keyword_weight: float = 0.3,
    ) -> list[MemoryEntry]:
        """检索记忆.

        支持三种检索策略：语义检索、关键词检索、混合检索。
        支持元数据过滤（category）和重要性过滤。

        性能优化：
        - L0: 查询结果缓存
        - L1: 精确查询快速路径
        - 性能统计追踪

        Args:
            query: 查询文本。
            top_k: 返回的最大条目数。
            category: 可选的分类过滤。
            min_importance: 最小重要性过滤。
            strategy: 检索策略，默认为 HYBRID。
            similarity_threshold: 向量检索相似度阈值 (0.0-1.0)，默认 0.5。
            keyword_weight: 混合检索中关键词检索的权重，默认 0.3。

        Returns:
            匹配的记忆条目列表。
        """
        start_time = time.time()

        cache_key = self._generate_cache_key(query, category, strategy, top_k)
        cached_results = self._get_from_cache(cache_key)
        if cached_results is not None:
            response_time = (time.time() - start_time) * 1000
            self._update_stats(response_time, cache_hit=True)
            logger.debug(f"[缓存命中] 查询: {query}")
            return cached_results[:top_k]

        exact_hit = False
        vector_hit = False
        keyword_hit = False
        results: list[MemoryEntry] = []

        if self._is_exact_query(query) and strategy != RetrievalStrategy.SEMANTIC:
            results = self._exact_match(query, category)
            if results:
                exact_hit = True
                logger.debug(f"[精确匹配] 查询: {query} -> 找到 {len(results)} 条")

        if not results:
            if strategy == RetrievalStrategy.SEMANTIC:
                results = self._recall_semantic(
                    query, top_k, category, min_importance, similarity_threshold
                )
                vector_hit = True
            elif strategy == RetrievalStrategy.KEYWORD:
                results = self._recall_from_entries(query, top_k, category, min_importance)
                keyword_hit = True
            else:
                results = self._recall_hybrid(
                    query, top_k, category, min_importance, similarity_threshold, keyword_weight
                )
                vector_hit = self._vectorstore is not None

        if min_importance > 0:
            results = [e for e in results if e.importance >= min_importance]
        results = results[:top_k]

        response_time = (time.time() - start_time) * 1000
        self._update_stats(
            response_time,
            exact_hit=exact_hit,
            keyword_hit=keyword_hit,
            vector_hit=vector_hit,
        )

        if results:
            self._update_cache(cache_key, results)
            logger.debug(
                f"[检索完成] 查询: {query} -> 找到 {len(results)} 条, "
                f"耗时: {response_time:.2f}ms"
            )

        return results

    def _recall_semantic(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_importance: float = 0.0,
        similarity_threshold: float = 0.5,
    ) -> list[MemoryEntry]:
        """仅使用向量语义检索.

        Args:
            query: 查询文本。
            top_k: 返回的最大条目数。
            category: 可选的分类过滤。
            min_importance: 最小重要性过滤。
            similarity_threshold: 相似度阈值。

        Returns:
            匹配的记忆条目列表。
        """
        if not self._vectorstore:
            logger.debug("Vector store not available, falling back to keyword search")
            return self._recall_from_entries(query, top_k, category, min_importance)

        try:
            filter_dict = None
            if category:
                filter_dict = {"category": category}

            results = self._vectorstore.recall(
                query, k=top_k * 2, filter=filter_dict, similarity_threshold=similarity_threshold
            )
            entries = []
            for r in results:
                entry = MemoryEntry(
                    content=r["content"],
                    importance=r.get("metadata", {}).get("importance", 0.5),
                    category=r.get("metadata", {}).get("category", "general"),
                    source=r.get("metadata", {}).get("source", "manual"),
                )
                if entry.importance >= min_importance:
                    entries.append(entry)
            if entries:
                logger.debug(f"Semantic recall found {len(entries)} entries for '{query}'")
                return entries[:top_k]
        except Exception as e:
            logger.debug(f"Semantic recall failed: {e}")

        return []

    def _recall_hybrid(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_importance: float = 0.0,
        similarity_threshold: float = 0.5,
        keyword_weight: float = 0.3,
    ) -> list[MemoryEntry]:
        """混合检索：向量语义 + 关键词，RRF 融合.

        Args:
            query: 查询文本。
            top_k: 返回的最大条目数。
            category: 可选的分类过滤。
            min_importance: 最小重要性过滤。
            similarity_threshold: 向量检索相似度阈值。
            keyword_weight: 关键词检索权重。

        Returns:
            匹配的记忆条目列表。
        """
        semantic_results: list[tuple[MemoryEntry, float]] = []
        keyword_results: list[tuple[MemoryEntry, float]] = []

        # 1. 执行向量语义检索
        if self._vectorstore:
            try:
                filter_dict = None
                if category:
                    filter_dict = {"category": category}

                vector_results = self._vectorstore.recall(
                    query,
                    k=top_k * 2,
                    filter=filter_dict,
                    similarity_threshold=similarity_threshold,
                )
                for r in vector_results:
                    entry = MemoryEntry(
                        content=r["content"],
                        importance=r.get("metadata", {}).get("importance", 0.5),
                        category=r.get("metadata", {}).get("category", "general"),
                        source=r.get("metadata", {}).get("source", "manual"),
                    )
                    if entry.importance >= min_importance:
                        similarity = r.get("similarity", 0.5)
                        semantic_results.append((entry, similarity))
            except Exception as e:
                logger.debug(f"Hybrid semantic recall failed: {e}")

        # 2. 执行关键词检索（获取带分数的结果）
        keyword_entries = self._recall_from_entries_with_scores(
            query, top_k * 2, category, min_importance
        )
        keyword_results = [(entry, score) for entry, score in keyword_entries]

        # 3. 如果没有向量结果，直接返回关键词结果
        if not semantic_results:
            logger.debug(f"Keyword recall found {len(keyword_results)} entries for '{query}'")
            return [entry for entry, _ in keyword_results[:top_k]]

        # 4. 如果没有关键词结果，直接返回向量结果
        if not keyword_results:
            logger.debug(f"Semantic recall found {len(semantic_results)} entries for '{query}'")
            return [entry for entry, _ in semantic_results[:top_k]]

        # 5. RRF 融合结果
        semantic_weight = 1.0 - keyword_weight
        fused_results = self._reciprocal_rank_fusion(
            semantic_results, keyword_results, semantic_weight, keyword_weight
        )

        logger.debug(
            f"Hybrid recall: semantic={len(semantic_results)}, "
            f"keyword={len(keyword_results)}, fused={len(fused_results)} for '{query}'"
        )

        return fused_results[:top_k]

    def _recall_from_entries_with_scores(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_importance: float = 0.0,
    ) -> list[tuple[MemoryEntry, float]]:
        """从本地条目检索，返回带分数的结果.

        Args:
            query: 查询文本。
            top_k: 返回的最大条目数。
            category: 可选的分类过滤。
            min_importance: 最小重要性过滤。

        Returns:
            带分数的记忆条目列表。
        """
        query_lower = query.lower()
        scored_entries: list[tuple[MemoryEntry, float]] = []

        for entry in self._entries:
            if category and entry.category != category:
                continue
            if entry.importance < min_importance:
                continue

            score = entry.importance

            if query_lower in entry.content.lower():
                score += 0.5

            query_words = set(query_lower.split())
            content_words = set(entry.content.lower().split())
            overlap = len(query_words & content_words)
            score += overlap * 0.1

            scored_entries.append((entry, score))

        scored_entries.sort(key=lambda x: x[1], reverse=True)

        return scored_entries[:top_k]

    def _recall_from_entries(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """从本地条目检索（简单文本匹配）.

        Args:
            query: 查询文本。
            top_k: 返回的最大条目数。
            category: 可选的分类过滤。
            min_importance: 最小重要性过滤。

        Returns:
            匹配的记忆条目列表。
        """
        query_lower = query.lower()
        scored_entries: list[tuple[MemoryEntry, float]] = []

        for entry in self._entries:
            if category and entry.category != category:
                continue
            if entry.importance < min_importance:
                continue

            score = entry.importance

            if query_lower in entry.content.lower():
                score += 0.5

            query_words = set(query_lower.split())
            content_words = set(entry.content.lower().split())
            overlap = len(query_words & content_words)
            score += overlap * 0.1

            scored_entries.append((entry, score))

        scored_entries.sort(key=lambda x: x[1], reverse=True)

        return [e[0] for e in scored_entries[:top_k]]

    def get_all_entries(
        self,
        category: str | None = None,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """获取所有记忆条目.

        Args:
            category: 可选的分类过滤。
            min_importance: 最小重要性过滤。

        Returns:
            记忆条目列表。
        """
        entries = self._entries

        if category:
            entries = [e for e in entries if e.category == category]
        if min_importance > 0:
            entries = [e for e in entries if e.importance >= min_importance]

        return sorted(entries, key=lambda x: x.importance, reverse=True)

    def forget(self, content_pattern: str) -> int:
        """删除匹配的记忆.

        同时从 JSON 存储和向量存储中删除。

        Args:
            content_pattern: 内容匹配模式。

        Returns:
            删除的条目数。
        """
        pattern = re.compile(content_pattern, re.IGNORECASE)
        original_count = len(self._entries)

        # 找出要删除的条目（用于后续向量存储删除）
        entries_to_remove = [e for e in self._entries if pattern.search(e.content)]

        # 从 JSON 存储删除
        self._entries = [e for e in self._entries if not pattern.search(e.content)]

        removed = original_count - len(self._entries)
        if removed > 0:
            self._save_entries()
            logger.info(f"Removed {removed} memory entries from JSON store")

            # 从向量存储删除
            if self._vectorstore:
                for entry in entries_to_remove:
                    try:
                        # 使用内容作为查询条件删除 (ChromaDB 使用 where 参数)
                        self._vectorstore.delete(where={"content": entry.content})
                    except Exception as e:
                        logger.debug(f"Failed to remove from vector store: {e}")

        return removed

    def get_memory_context(self, query: str | None = None, max_entries: int = 10) -> str:
        """获取用于 Agent 的记忆上下文.

        Args:
            query: 可选的查询文本（用于语义检索）。
            max_entries: 最大条目数。

        Returns:
            格式化的记忆上下文。
        """
        if not self._entries:
            return ""

        if query:
            entries = self.recall(query, top_k=max_entries)
        else:
            entries = sorted(
                self._entries,
                key=lambda x: x.importance,
                reverse=True,
            )[:max_entries]

        if not entries:
            return ""

        lines = ["## 记忆库"]
        for entry in entries:
            lines.append(f"- [{entry.category}] {entry.content}")

        return "\n".join(lines)
