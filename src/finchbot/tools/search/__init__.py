"""搜索引擎模块.

支持多搜索引擎自动降级：
1. Tavily - 搜索质量最好，专为 AI 设计
2. Brave Search - 免费额度大，隐私友好
3. DuckDuckGo - 无依赖备选，始终可用
"""

from finchbot.tools.search.base import SearchEngineType, SearchResult
from finchbot.tools.search.brave import BraveSearchEngine
from finchbot.tools.search.ddg import DuckDuckGoSearchEngine
from finchbot.tools.search.manager import SearchEngineManager
from finchbot.tools.search.tavily import TavilySearchEngine

__all__ = [
    "SearchEngineType",
    "SearchResult",
    "SearchEngineManager",
    "TavilySearchEngine",
    "BraveSearchEngine",
    "DuckDuckGoSearchEngine",
]
