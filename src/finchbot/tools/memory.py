"""记忆管理工具.

提供 Agent 主动保存和检索记忆的能力。
"""

from typing import Any

from pydantic import Field

from finchbot.i18n import t
from finchbot.tools.base import FinchTool


class RememberTool(FinchTool):
    """保存重要信息到记忆库.

    用于保存用户偏好、重要事实、任务目标等信息。
    """

    name: str = Field(default="remember", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)

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
        from pathlib import Path

        from finchbot.memory import EnhancedMemoryStore

        workspace = (
            Path(self.workspace) if self.workspace else Path.home() / ".finchbot" / "workspace"
        )
        store = EnhancedMemoryStore(workspace)

        entry = store.remember(
            content=content,
            importance=importance,
            category=category,
        )

        return f"✅ Remembered: {content[:50]}... (importance: {entry.importance:.2f}, category: {entry.category})"


class RecallTool(FinchTool):
    """从记忆库检索信息.

    根据查询内容检索相关的记忆条目。
    """

    name: str = Field(default="recall", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)

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
                "strategy": {
                    "type": "string",
                    "description": t("tools.recall.param_strategy"),
                    "enum": ["semantic", "keyword", "hybrid"],
                    "default": "hybrid",
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

    def _run(
        self,
        query: str,
        category: str | None = None,
        top_k: int = 5,
        strategy: str = "hybrid",
        similarity_threshold: float = 0.5,
    ) -> str:
        """执行记忆检索.

        Args:
            query: 查询内容。
            category: 可选的分类过滤。
            top_k: 最大返回数量。
            strategy: 检索策略 (semantic/keyword/hybrid)。
            similarity_threshold: 相似度阈值 (0.0-1.0)。

        Returns:
            检索结果字符串。
        """
        from pathlib import Path

        from finchbot.memory import EnhancedMemoryStore, RetrievalStrategy

        workspace = (
            Path(self.workspace) if self.workspace else Path.home() / ".finchbot" / "workspace"
        )
        store = EnhancedMemoryStore(workspace)

        # 将字符串策略转换为枚举
        strategy_enum = RetrievalStrategy(strategy.lower())

        entries = store.recall(
            query=query,
            top_k=top_k,
            category=category,
            strategy=strategy_enum,
            similarity_threshold=similarity_threshold,
        )

        if not entries:
            return f"No memories found for: {query}"

        lines = [f"## Found {len(entries)} memories:\n"]
        for i, entry in enumerate(entries, 1):
            lines.append(f"{i}. [{entry.category}] {entry.content}")
            lines.append(f"   Importance: {entry.importance:.2f} | Source: {entry.source}")
            lines.append("")

        return "\n".join(lines)


class ForgetTool(FinchTool):
    """从记忆库删除信息.

    根据内容模式删除匹配的记忆条目。
    """

    name: str = Field(default="forget", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)

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
                    "description": "要删除的内容匹配模式",
                },
            },
            "required": ["pattern"],
        }

    def _run(self, pattern: str) -> str:
        """执行记忆删除.

        Args:
            pattern: 内容匹配模式。

        Returns:
            操作结果消息。
        """
        from pathlib import Path

        from finchbot.memory import EnhancedMemoryStore

        workspace = (
            Path(self.workspace) if self.workspace else Path.home() / ".finchbot" / "workspace"
        )
        store = EnhancedMemoryStore(workspace)

        removed = store.forget(pattern)

        if removed > 0:
            return f"✅ Removed {removed} memory entries matching: {pattern}"
        return f"No memories found matching: {pattern}"
