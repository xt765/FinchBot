"""检索服务模块.

提供基于 Weighted RRF 的混合检索功能。
"""

from typing import Any, Optional

from loguru import logger

from finchbot.memory.storage.sqlite import SQLiteStore
from finchbot.memory.storage.vector import VectorMemoryStore
from finchbot.memory.types import QueryType


class RetrievalService:
    """检索服务."""

    def __init__(
        self,
        sqlite_store: SQLiteStore,
        vector_store: Optional[VectorMemoryStore] = None,
    ):
        """初始化检索服务.

        Args:
            sqlite_store: SQLite 存储实例。
            vector_store: 向量存储实例。
        """
        self.sqlite_store = sqlite_store
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        query_type: QueryType = QueryType.COMPLEX,
        top_k: int = 5,
        category: Optional[str] = None,
        similarity_threshold: float = 0.5,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """执行混合检索.

        Args:
            query: 查询内容。
            query_type: 查询类型。
            top_k: 最大返回数量。
            category: 分类过滤。
            similarity_threshold: 相似度阈值。
            include_archived: 是否包含归档的记忆。

        Returns:
            记忆列表。
        """
        weights = self._get_weights(query_type)
        keyword_weight = weights["keyword"]
        vector_weight = weights["vector"]

        # 优化：纯关键词检索
        if keyword_weight >= 0.99 and vector_weight <= 0.01:
            return self.sqlite_store.search_memories(
                query=query,
                category=category,
                include_archived=include_archived,
                limit=top_k,
            )

        # 优化：纯语义检索
        if vector_weight >= 0.99 and keyword_weight <= 0.01:
            if not self.vector_store:
                logger.warning("Vector store not available for semantic search, falling back to keyword")
                return self.sqlite_store.search_memories(
                    query=query,
                    category=category,
                    include_archived=include_archived,
                    limit=top_k,
                )
            
            vector_results = self.vector_store.recall(
                query=query,
                k=top_k,
                filter={"category": category} if category else None,
                similarity_threshold=similarity_threshold,
            )
            return self._fetch_full_memories(vector_results, include_archived)

        # 混合检索
        return self._weighted_rrf(
            query=query,
            keyword_weight=keyword_weight,
            vector_weight=vector_weight,
            top_k=top_k,
            category=category,
            similarity_threshold=similarity_threshold,
            include_archived=include_archived,
        )

    def _get_weights(self, query_type: QueryType) -> dict[str, float]:
        """获取查询类型的权重配置."""
        weights = {
            QueryType.KEYWORD_ONLY: {"keyword": 1.0, "vector": 0.0},
            QueryType.SEMANTIC_ONLY: {"keyword": 0.0, "vector": 1.0},
            QueryType.FACTUAL: {"keyword": 0.8, "vector": 0.2},
            QueryType.CONCEPTUAL: {"keyword": 0.2, "vector": 0.8},
            QueryType.COMPLEX: {"keyword": 0.5, "vector": 0.5},
            QueryType.AMBIGUOUS: {"keyword": 0.3, "vector": 0.7},
        }
        return weights.get(query_type, {"keyword": 0.5, "vector": 0.5})

    def _weighted_rrf(
        self,
        query: str,
        keyword_weight: float,
        vector_weight: float,
        top_k: int,
        category: Optional[str],
        similarity_threshold: float,
        include_archived: bool,
        k: int = 60,
    ) -> list[dict[str, Any]]:
        """执行加权 RRF 融合."""
        # 1. 获取关键词检索结果
        keyword_results = []
        if keyword_weight > 0.01:
            keyword_results = self.sqlite_store.search_memories(
                query=query,
                category=category,
                include_archived=include_archived,
                limit=top_k * 2,  # 获取更多候选用于重排
            )

        # 2. 获取向量检索结果
        vector_results = []
        if vector_weight > 0.01 and self.vector_store:
            vector_results_raw = self.vector_store.recall(
                query=query,
                k=top_k * 2,
                filter={"category": category} if category else None,
                similarity_threshold=similarity_threshold,
            )
            # 转换为统一格式，只保留ID和相似度
            vector_results = [
                {"id": r["id"], "similarity": r["similarity"]} for r in vector_results_raw
            ]

        # 3. RRF 计算
        scores: dict[str, float] = {}
        
        # 关键词结果打分
        for rank, item in enumerate(keyword_results):
            memory_id = item["id"]
            score = keyword_weight * (1.0 / (k + rank + 1))
            scores[memory_id] = scores.get(memory_id, 0.0) + score

        # 向量结果打分
        for rank, item in enumerate(vector_results):
            memory_id = item["id"]
            score = vector_weight * (1.0 / (k + rank + 1))
            scores[memory_id] = scores.get(memory_id, 0.0) + score

        # 4. 排序并获取最终结果
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
        
        final_results = []
        for memory_id in sorted_ids:
            memory = self.sqlite_store.get_memory(memory_id)
            if memory:
                # 附加混合分数和相似度信息（如果有）
                memory["_rrf_score"] = scores[memory_id]
                # 尝试从向量结果中找回相似度
                for v_res in vector_results:
                    if v_res["id"] == memory_id:
                        memory["similarity"] = v_res["similarity"]
                        break
                final_results.append(memory)

        return final_results

    def _fetch_full_memories(
        self, vector_results: list[dict[str, Any]], include_archived: bool
    ) -> list[dict[str, Any]]:
        """获取完整的记忆详情."""
        memories = []
        for res in vector_results:
            memory_id = res.get("id")
            if not memory_id:
                continue
            
            memory = self.sqlite_store.get_memory(memory_id)
            if not memory:
                continue
                
            if not include_archived and memory.get("is_archived"):
                continue
                
            memory["similarity"] = res.get("similarity")
            memories.append(memory)
            
        return memories
