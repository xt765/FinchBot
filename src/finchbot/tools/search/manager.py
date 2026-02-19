"""搜索引擎管理器.

实现多搜索引擎自动降级机制：
1. Tavily - 搜索质量最好，专为 AI 设计
2. Brave Search - 免费额度大，隐私友好
3. DuckDuckGo - 无依赖备选，始终可用
"""

import logging
from typing import Any

from finchbot.tools.search.base import (
    BaseSearchEngine,
    SearchEngineType,
    SearchResponse,
)
from finchbot.tools.search.brave import BraveSearchEngine
from finchbot.tools.search.ddg import DuckDuckGoSearchEngine
from finchbot.tools.search.tavily import TavilySearchEngine

logger = logging.getLogger(__name__)

DEFAULT_ENGINE_ORDER = [
    SearchEngineType.TAVILY,
    SearchEngineType.BRAVE,
    SearchEngineType.DUCKDUCKGO,
]


class SearchEngineManager:
    """搜索引擎管理器.

    管理多个搜索引擎，实现自动降级机制。
    当首选引擎不可用或搜索失败时，自动切换到下一个引擎。

    Attributes:
        engines: 引擎实例字典。
        engine_order: 引擎优先级顺序。
        fallback_on_error: 是否在错误时自动降级。
    """

    def __init__(
        self,
        engine_order: list[SearchEngineType] | None = None,
        fallback_on_error: bool = True,
        **engine_configs: Any,
    ):
        """初始化搜索引擎管理器.

        Args:
            engine_order: 引擎优先级顺序（默认：Tavily > Brave > DuckDuckGo）。
            fallback_on_error: 是否在错误时自动降级。
            **engine_configs: 各引擎的配置参数。
                例如：tavily_api_key="xxx", brave_api_key="yyy"
        """
        self.engine_order = engine_order or DEFAULT_ENGINE_ORDER.copy()
        self.fallback_on_error = fallback_on_error
        self._engines: dict[SearchEngineType, BaseSearchEngine] = {}

        self._init_engines(engine_configs)

    def _init_engines(self, configs: dict[str, Any]) -> None:
        """初始化搜索引擎实例.

        Args:
            configs: 引擎配置参数。
        """
        tavily_config = {
            k.replace("tavily_", ""): v for k, v in configs.items() if k.startswith("tavily_")
        }
        if "api_key" not in tavily_config and "TAVILY_API_KEY" in configs:
            tavily_config["api_key"] = configs["TAVILY_API_KEY"]
        self._engines[SearchEngineType.TAVILY] = TavilySearchEngine(**tavily_config)

        brave_config = {
            k.replace("brave_", ""): v for k, v in configs.items() if k.startswith("brave_")
        }
        if "api_key" not in brave_config and "BRAVE_API_KEY" in configs:
            brave_config["api_key"] = configs["BRAVE_API_KEY"]
        self._engines[SearchEngineType.BRAVE] = BraveSearchEngine(**brave_config)

        ddg_config = {k.replace("ddg_", ""): v for k, v in configs.items() if k.startswith("ddg_")}
        self._engines[SearchEngineType.DUCKDUCKGO] = DuckDuckGoSearchEngine(**ddg_config)

    def get_engine(self, engine_type: SearchEngineType) -> BaseSearchEngine | None:
        """获取指定类型的搜索引擎.

        Args:
            engine_type: 引擎类型。

        Returns:
            搜索引擎实例，如果不存在则返回 None。
        """
        return self._engines.get(engine_type)

    def get_available_engines(self) -> list[SearchEngineType]:
        """获取所有可用的搜索引擎.

        Returns:
            可用引擎类型列表（按优先级排序）。
        """
        available = []
        for engine_type in self.engine_order:
            engine = self._engines.get(engine_type)
            if engine and engine.is_available:
                available.append(engine_type)
        return available

    def search(
        self,
        query: str,
        max_results: int = 5,
        preferred_engine: SearchEngineType | None = None,
        **kwargs: Any,
    ) -> SearchResponse:
        """执行搜索，支持自动降级.

        Args:
            query: 搜索查询。
            max_results: 最大结果数。
            preferred_engine: 首选引擎（可选）。
            **kwargs: 传递给搜索引擎的额外参数。

        Returns:
            搜索响应。
        """
        if preferred_engine:
            engine_order = [preferred_engine] + [
                e for e in self.engine_order if e != preferred_engine
            ]
        else:
            engine_order = self.engine_order

        errors: list[str] = []

        for engine_type in engine_order:
            engine = self._engines.get(engine_type)
            if not engine:
                continue

            if not engine.is_available:
                logger.debug(f"Engine {engine_type.value} not available, skipping")
                continue

            logger.info(f"Trying search with {engine_type.value}")
            response = engine.search(query, max_results, **kwargs)

            if response.is_success:
                return response

            if response.error:
                errors.append(f"{engine_type.value}: {response.error}")
                logger.warning(f"Search failed with {engine_type.value}: {response.error}")

            if not self.fallback_on_error:
                return response

        all_errors = "; ".join(errors) if errors else "No engines available"
        return SearchResponse(
            engine=SearchEngineType.DUCKDUCKGO,
            query=query,
            error=f"All search engines failed: {all_errors}",
        )

    def search_with_all(
        self,
        query: str,
        max_results: int = 5,
        **kwargs: Any,
    ) -> dict[SearchEngineType, SearchResponse]:
        """使用所有可用引擎搜索（用于对比测试）.

        Args:
            query: 搜索查询。
            max_results: 最大结果数。
            **kwargs: 传递给搜索引擎的额外参数。

        Returns:
            各引擎的搜索响应字典。
        """
        responses: dict[SearchEngineType, SearchResponse] = {}

        for engine_type in self.engine_order:
            engine = self._engines.get(engine_type)
            if engine and engine.is_available:
                responses[engine_type] = engine.search(query, max_results, **kwargs)

        return responses
