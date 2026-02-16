"""Tavily 搜索引擎实现.

Tavily 是专为 AI Agent 设计的搜索引擎，搜索质量最好。
API 文档: https://docs.tavily.com/
"""

import os
from typing import Any

from finchbot.tools.search.base import (
    BaseSearchEngine,
    SearchEngineType,
    SearchResponse,
    SearchResult,
)

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[misc,assignment]
    HTTPX_AVAILABLE = False

TAVILY_API_URL = "https://api.tavily.com"


class TavilySearchEngine(BaseSearchEngine):
    """Tavily 搜索引擎.

    专为 AI Agent 优化的搜索引擎，提供高质量搜索结果。

    Attributes:
        api_key: Tavily API 密钥。
        search_depth: 搜索深度 ("basic" 或 "advanced")。
        include_domains: 限制搜索的域名列表。
        exclude_domains: 排除的域名列表。
    """

    engine_type = SearchEngineType.TAVILY

    def __init__(
        self,
        api_key: str | None = None,
        search_depth: str = "basic",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ):
        """初始化 Tavily 搜索引擎.

        Args:
            api_key: Tavily API 密钥（可选，优先使用环境变量）。
            search_depth: 搜索深度。
            include_domains: 包含域名列表。
            exclude_domains: 排除域名列表。
        """
        self._api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.search_depth = search_depth
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains

    @property
    def is_available(self) -> bool:
        """检查 Tavily 是否可用."""
        return self._api_key is not None and HTTPX_AVAILABLE

    def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs: Any,
    ) -> SearchResponse:
        """执行 Tavily 搜索.

        Args:
            query: 搜索查询。
            max_results: 最大结果数。
            **kwargs: 额外参数 (search_depth, include_domains, exclude_domains)。

        Returns:
            搜索响应。
        """
        if not self._api_key:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error="TAVILY_API_KEY not configured",
            )

        if not HTTPX_AVAILABLE or httpx is None:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error="httpx not installed. Run: uv add httpx",
            )

        payload: dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "search_depth": kwargs.get("search_depth", self.search_depth),
        }

        include_domains = kwargs.get("include_domains", self.include_domains)
        exclude_domains = kwargs.get("exclude_domains", self.exclude_domains)

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        try:
            response = httpx.post(
                f"{TAVILY_API_URL}/search",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error=f"HTTP {e.response.status_code}: {e.response.text}",
            )
        except httpx.TimeoutException:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error="Request timeout",
            )
        except Exception as e:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error=str(e),
            )

        results = []
        for item in data.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", "No title"),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    score=item.get("score", 0.0),
                    source=self.engine_type,
                    raw_data=item,
                )
            )

        return SearchResponse(
            results=results,
            engine=self.engine_type,
            query=query,
            total=len(results),
        )
