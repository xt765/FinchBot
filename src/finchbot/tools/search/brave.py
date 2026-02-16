"""Brave Search 搜索引擎实现.

Brave Search 提供免费额度大，隐私友好的搜索服务。
API 文档: https://brave.com/search/api/
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

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchEngine(BaseSearchEngine):
    """Brave Search 搜索引擎.

    免费额度大，隐私友好的搜索引擎。

    Attributes:
        api_key: Brave Search API 密钥。
        country: 国家代码 (如 "us", "cn")。
        search_lang: 搜索语言 (如 "en", "zh-hans")。
    """

    engine_type = SearchEngineType.BRAVE

    def __init__(
        self,
        api_key: str | None = None,
        country: str | None = None,
        search_lang: str | None = None,
    ):
        """初始化 Brave Search 搜索引擎.

        Args:
            api_key: Brave Search API 密钥（可选，优先使用环境变量）。
            country: 国家代码。
            search_lang: 搜索语言。
        """
        self._api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.country = country or os.getenv("BRAVE_COUNTRY", "us")
        self.search_lang = search_lang or os.getenv("BRAVE_SEARCH_LANG", "en")

    @property
    def is_available(self) -> bool:
        """检查 Brave Search 是否可用."""
        return self._api_key is not None and HTTPX_AVAILABLE

    def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs: Any,
    ) -> SearchResponse:
        """执行 Brave Search 搜索.

        Args:
            query: 搜索查询。
            max_results: 最大结果数。
            **kwargs: 额外参数 (country, search_lang)。

        Returns:
            搜索响应。
        """
        if not self._api_key:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error="BRAVE_API_KEY not configured",
            )

        if not HTTPX_AVAILABLE or httpx is None:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error="httpx not installed. Run: uv add httpx",
            )

        params: dict[str, Any] = {
            "q": query,
            "count": max_results,
            "country": kwargs.get("country", self.country),
            "search_lang": kwargs.get("search_lang", self.search_lang),
            "text_decorations": False,
            "safesearch": "moderate",
        }

        try:
            response = httpx.get(
                BRAVE_API_URL,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self._api_key,
                },
                params=params,
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
        web_results = data.get("web", {}).get("results", [])

        for item in web_results[:max_results]:
            description = item.get("description", "") or item.get("text", "")
            results.append(
                SearchResult(
                    title=item.get("title", "No title"),
                    url=item.get("url", ""),
                    snippet=description,
                    score=1.0 - (len(results) * 0.1),
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
