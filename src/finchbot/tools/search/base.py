"""搜索引擎基类和数据模型."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SearchEngineType(StrEnum):
    """搜索引擎类型."""

    TAVILY = "tavily"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"


@dataclass
class SearchResult:
    """搜索结果数据类.

    Attributes:
        title: 结果标题。
        url: 结果链接。
        snippet: 内容摘要。
        score: 相关性分数 (0-1)。
        source: 来源搜索引擎。
        raw_data: 原始数据（可选）。
    """

    title: str
    url: str
    snippet: str = ""
    score: float = 0.0
    source: SearchEngineType = SearchEngineType.DUCKDUCKGO
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "score": self.score,
            "source": self.source.value,
        }


@dataclass
class SearchResponse:
    """搜索响应数据类.

    Attributes:
        results: 搜索结果列表。
        engine: 使用的搜索引擎。
        query: 搜索查询。
        total: 总结果数。
        error: 错误信息（如果有）。
    """

    results: list[SearchResult] = field(default_factory=list)
    engine: SearchEngineType = SearchEngineType.DUCKDUCKGO
    query: str = ""
    total: int = 0
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """是否搜索成功."""
        return self.error is None and len(self.results) > 0

    def to_formatted_text(self, max_snippet_length: int = 500) -> str:
        """格式化为文本输出.

        Args:
            max_snippet_length: 摘要最大长度。

        Returns:
            格式化后的文本。
        """
        if self.error:
            return f"Search Error ({self.engine.value}): {self.error}"

        if not self.results:
            return f"No results found for '{self.query}'"

        lines = [f"## Search Results: {self.query}", f"*Source: {self.engine.value}*", ""]

        for i, result in enumerate(self.results, 1):
            lines.append(f"### {i}. {result.title}")
            lines.append(f"**URL**: {result.url}")
            lines.append(f"**Score**: {result.score:.2f}")

            snippet = result.snippet
            if len(snippet) > max_snippet_length:
                snippet = snippet[:max_snippet_length] + "..."
            lines.append(f"**Summary**: {snippet}")
            lines.append("")

        return "\n".join(lines)


class BaseSearchEngine(ABC):
    """搜索引擎基类.

    所有搜索引擎实现必须继承此类。
    """

    engine_type: SearchEngineType

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用（API Key 配置等）."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs: Any,
    ) -> SearchResponse:
        """执行搜索.

        Args:
            query: 搜索查询。
            max_results: 最大结果数。
            **kwargs: 额外参数。

        Returns:
            搜索响应。
        """
        pass

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本.

        Args:
            text: 原始文本。
            max_length: 最大长度。

        Returns:
            截断后的文本。
        """
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
