"""记忆管理工具.

提供 Agent 主动保存和检索记忆的能力。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import Field

from finchbot.i18n import t
from finchbot.tools.base import FinchTool

if TYPE_CHECKING:
    from finchbot.memory import MemoryManager


class RememberTool(FinchTool):
    """保存重要信息到记忆库.

    用于保存用户偏好、重要事实、任务目标等信息。
    """

    name: str = Field(default="remember", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)
    memory_manager: Any = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        desc = t("tools.remember.description")
        hint = t("tools.remember.hint")
        self.description = f"{desc} {hint}" if hint != "tools.remember.hint" else desc

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": t("tools.remember.param_content"),
                },
                "category": {
                    "type": "string",
                    "description": t("tools.remember.param_category"),
                    "default": "general",
                },
                "importance": {
                    "type": "number",
                    "description": t("tools.remember.param_importance"),
                    "default": 0.5,
                },
            },
            "required": ["content"],
        }

    def _get_manager(self) -> MemoryManager:
        """获取或创建 MemoryManager 实例."""
        if self.memory_manager is not None:
            return self.memory_manager
        from finchbot.memory import MemoryManager

        workspace = (
            Path(self.workspace) if self.workspace else Path.home() / ".finchbot" / "workspace"
        )
        return MemoryManager(workspace)

    def _run(
        self,
        content: str,
        category: str = "general",
        importance: float = 0.5,
    ) -> str:
        """执行记忆保存.

        Args:
            content: 要保存的内容。
            category: 分类标签。
            importance: 重要性评分。

        Returns:
            操作结果消息。
        """
        manager = self._get_manager()

        memory = manager.remember(
            content=content,
            importance=importance,
            category=category,
        )

        if memory:
            return f"✅ Remembered: {content[:50]}... (importance: {memory['importance']:.2f}, category: {memory['category']})"
        return "❌ Failed to remember"


class RecallTool(FinchTool):
    """从记忆库检索信息.

    根据查询内容检索相关的记忆条目。
    """

    name: str = Field(default="recall", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)
    memory_manager: Any = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        desc = t("tools.recall.description")
        hint = t("tools.recall.hint")
        self.description = f"{desc} {hint}" if hint != "tools.recall.hint" else desc

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": t("tools.recall.param_query"),
                },
                "category": {
                    "type": "string",
                    "description": t("tools.recall.param_category"),
                },
                "top_k": {
                    "type": "integer",
                    "description": t("tools.recall.param_top_k"),
                    "default": 5,
                },
                "query_type": {
                    "type": "string",
                    "description": t("tools.recall.param_query_type"),
                    "enum": [
                        "keyword_only",
                        "semantic_only",
                        "factual",
                        "conceptual",
                        "complex",
                        "ambiguous",
                    ],
                    "default": "complex",
                },
                "similarity_threshold": {
                    "type": "number",
                    "description": t("tools.recall.param_similarity_threshold"),
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5,
                },
            },
            "required": ["query"],
        }

    def _get_manager(self) -> MemoryManager:
        """获取或创建 MemoryManager 实例."""
        if self.memory_manager is not None:
            return self.memory_manager
        from finchbot.memory import MemoryManager

        workspace = (
            Path(self.workspace) if self.workspace else Path.home() / ".finchbot" / "workspace"
        )
        return MemoryManager(workspace)

    def _run(
        self,
        query: str,
        category: str | None = None,
        top_k: int = 5,
        query_type: str = "complex",
        similarity_threshold: float = 0.5,
    ) -> str:
        """执行记忆检索.

        Args:
            query: 查询内容。
            category: 可选的分类过滤。
            top_k: 最大返回数量。
            query_type: 查询类型。
            similarity_threshold: 相似度阈值 (0.0-1.0)。

        Returns:
            检索结果字符串。
        """
        from finchbot.memory import QueryType

        manager = self._get_manager()

        try:
            query_type_enum = QueryType(query_type.lower())
        except ValueError:
            query_type_enum = QueryType.COMPLEX

        memories = manager.recall(
            query=query,
            top_k=top_k,
            category=category,
            query_type=query_type_enum,
            similarity_threshold=similarity_threshold,
        )

        if not memories:
            return f"No memories found for: {query}"

        lines = [f"## Found {len(memories)} memories:\n"]
        for i, memory in enumerate(memories, 1):
            lines.append(f"{i}. [{memory['category']}] {memory['content']}")
            created_at = memory.get("created_at", "Unknown")
            similarity = memory.get("similarity")
            similarity_str = f" | Similarity: {similarity:.2f}" if similarity else ""
            rrf_score = memory.get("_rrf_score")
            rrf_str = f" | RRF Score: {rrf_score:.4f}" if rrf_score else ""
            lines.append(
                f"   Importance: {memory['importance']:.2f} | Source: {memory['source']} | Created: {created_at}{similarity_str}{rrf_str}"
            )
            lines.append("")

        return "\n".join(lines)


class ForgetTool(FinchTool):
    """从记忆库删除信息.

    根据内容模式删除匹配的记忆条目。
    """

    name: str = Field(default="forget", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)
    memory_manager: Any = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        desc = t("tools.forget.description")
        hint = t("tools.forget.hint")
        self.description = f"{desc} {hint}" if hint != "tools.forget.hint" else desc

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": t("tools.forget.param_pattern"),
                },
            },
            "required": ["pattern"],
        }

    def _get_manager(self) -> MemoryManager:
        """获取或创建 MemoryManager 实例."""
        if self.memory_manager is not None:
            return self.memory_manager
        from finchbot.memory import MemoryManager

        workspace = (
            Path(self.workspace) if self.workspace else Path.home() / ".finchbot" / "workspace"
        )
        return MemoryManager(workspace)

    def _run(self, pattern: str) -> str:
        """执行记忆删除.

        Args:
            pattern: 内容匹配模式。

        Returns:
            操作结果消息。
        """
        manager = self._get_manager()

        stats = manager.forget(pattern)

        total_found = stats.get("total_found", 0)
        deleted = stats.get("deleted", 0)
        archived = stats.get("archived", 0)

        if total_found > 0:
            return f"✅ Processed {total_found} memories (deleted: {deleted}, archived: {archived}) matching: {pattern}"
        return f"No memories found matching: {pattern}"
