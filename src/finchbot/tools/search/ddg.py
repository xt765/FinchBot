"""DuckDuckGo 搜索引擎实现.

DuckDuckGo 是无依赖的备选搜索引擎，始终可用，无需 API Key。
使用 ddgs 库实现 (原 duckduckgo-search)。
"""

from typing import Any

from finchbot.tools.search.base import (
    BaseSearchEngine,
    SearchEngineType,
    SearchResponse,
    SearchResult,
)

try:
    from ddgs import DDGS

    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS  # type: ignore[no-redef]

        DDGS_AVAILABLE = True
    except ImportError:
        DDGS = None  # type: ignore[misc,assignment]
        DDGS_AVAILABLE = False


_PRIMP_SUPPORTED_IMPERSONATES = (
    "chrome_144",
    "chrome_145",
    "edge_144",
    "edge_145",
    "opera_126",
    "opera_127",
    "safari_18.5",
    "safari_26",
    "firefox_140",
    "firefox_146",
    "random",
)


def _patch_ddgs_impersonates() -> None:
    """修复 ddgs 库与 primp 版本不兼容的问题.

    ddgs 库的 HttpClient._impersonates 列表包含了一些 primp 不支持的版本，
    导致警告 "Impersonate 'xxx' does not exist, using 'random'"。

    此函数将 ddgs 的 _impersonates 列表替换为 primp 支持的版本。
    """
    if not DDGS_AVAILABLE:
        return

    try:
        from ddgs.http_client import HttpClient
    except ImportError:
        return

    if hasattr(HttpClient, "_impersonates"):
        current = HttpClient._impersonates
        if current != _PRIMP_SUPPORTED_IMPERSONATES:
            HttpClient._impersonates = _PRIMP_SUPPORTED_IMPERSONATES


_patch_ddgs_impersonates()


class DuckDuckGoSearchEngine(BaseSearchEngine):
    """DuckDuckGo 搜索引擎.

    无需 API Key 的备选搜索引擎，始终可用。
    使用 ddgs 库实现。

    Attributes:
        region: 地区代码 (如 "us-en", "cn-zh")。
        safesearch: 安全搜索级别 ("on", "moderate", "off")。
        timelimit: 时间限制 ("d", "w", "m", "y")。
    """

    engine_type = SearchEngineType.DUCKDUCKGO

    def __init__(
        self,
        region: str = "us-en",
        safesearch: str = "moderate",
        timelimit: str | None = None,
    ):
        """初始化 DuckDuckGo 搜索引擎.

        Args:
            region: 地区代码。
            safesearch: 安全搜索级别。
            timelimit: 时间限制。
        """
        self.region = region
        self.safesearch = safesearch
        self.timelimit = timelimit

    @property
    def is_available(self) -> bool:
        """DuckDuckGo 始终可用（只要库已安装）."""
        return DDGS_AVAILABLE

    def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs: Any,
    ) -> SearchResponse:
        """执行 DuckDuckGo 搜索.

        Args:
            query: 搜索查询。
            max_results: 最大结果数。
            **kwargs: 额外参数 (region, safesearch, timelimit)。

        Returns:
            搜索响应。
        """
        if not DDGS_AVAILABLE or DDGS is None:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error="ddgs not installed. Run: uv add ddgs",
            )

        region = kwargs.get("region", self.region)
        safesearch = kwargs.get("safesearch", self.safesearch)
        timelimit = kwargs.get("timelimit", self.timelimit)

        try:
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=max_results,
                )

        except Exception as e:
            return SearchResponse(
                engine=self.engine_type,
                query=query,
                error=str(e),
            )

        results = []
        for i, item in enumerate(search_results):
            results.append(
                SearchResult(
                    title=item.get("title", "No title"),
                    url=item.get("href", "") or item.get("url", ""),
                    snippet=item.get("body", "") or item.get("description", ""),
                    score=1.0 - (i * 0.1),
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
