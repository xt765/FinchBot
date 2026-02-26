"""网页搜索工具.

支持多搜索引擎自动降级：
1. Tavily - 搜索质量最好，专为 AI 设计
2. Brave Search - 免费额度大，隐私友好
3. DuckDuckGo - 无依赖备选，始终可用
"""

import os
from typing import Any

from pydantic import Field

from finchbot.i18n import t
from finchbot.tools.base import FinchTool
from finchbot.tools.search import SearchEngineManager, SearchEngineType


class WebSearchTool(FinchTool):
    """网页搜索工具.

    支持多搜索引擎自动降级，确保始终能获取搜索结果。

    Attributes:
        max_results: 最大返回结果数。
        preferred_engine: 首选搜索引擎。
        fallback_on_error: 是否在错误时自动降级。
        tavily_api_key: Tavily API 密钥。
        brave_api_key: Brave Search API 密钥。
        search_depth: Tavily 搜索深度。
        include_domains: 限制搜索的域名列表。
        exclude_domains: 排除的域名列表。
    """

    name: str = Field(default="web_search", description="Tool name")
    description: str = Field(default="", description="Tool description")
    max_results: int = Field(default=5, description="Max results")
    preferred_engine: SearchEngineType | None = Field(
        default=None, description="Preferred search engine"
    )
    fallback_on_error: bool = Field(default=True, description="Fallback on error")

    tavily_api_key: str | None = Field(default=None, exclude=True)
    brave_api_key: str | None = Field(default=None, exclude=True)
    search_depth: str = Field(default="basic", description="Search depth for Tavily")
    include_domains: list[str] | None = Field(default=None, description="Include domains")
    exclude_domains: list[str] | None = Field(default=None, description="Exclude domains")

    _manager: SearchEngineManager | None = None

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        self.description = t("tools.web_search.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    def _get_manager(self) -> SearchEngineManager:
        """获取或创建搜索引擎管理器."""
        if self._manager is None:
            self._manager = SearchEngineManager(
                fallback_on_error=self.fallback_on_error,
                tavily_api_key=self.tavily_api_key,
                brave_api_key=self.brave_api_key,
            )
        return self._manager

    def _run(self, query: str, max_results: int | None = None) -> str:
        """执行网页搜索.

        Args:
            query: 搜索查询内容。
            max_results: 可选的最大结果数。

        Returns:
            搜索结果字符串。
        """
        manager = self._get_manager()
        max_res = max_results or self.max_results

        kwargs: dict[str, Any] = {}
        if self.include_domains:
            kwargs["include_domains"] = self.include_domains
        if self.exclude_domains:
            kwargs["exclude_domains"] = self.exclude_domains
        kwargs["search_depth"] = self.search_depth

        response = manager.search(
            query=query,
            max_results=max_res,
            preferred_engine=self.preferred_engine,
            **kwargs,
        )

        return response.to_formatted_text()


class WebExtractTool(FinchTool):
    """网页内容提取工具.

    从指定 URL 提取内容，返回结构化文本。
    使用 Tavily Extract API。

    Attributes:
        api_key: Tavily API 密钥。
        extract_depth: 提取深度，"basic" 或 "advanced"。
    """

    name: str = Field(default="web_extract", description="Tool name")
    description: str = Field(default="", description="Tool description")
    api_key: str | None = Field(default=None, exclude=True)
    extract_depth: str = Field(default="basic", description="Extract depth")

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        self.description = t("tools.web_extract.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URLs to extract",
                },
            },
            "required": ["urls"],
        }

    def _run(self, urls: list[str]) -> str:
        """提取网页内容.

        Args:
            urls: URL 列表。

        Returns:
            提取的内容字符串。
        """
        try:
            import httpx

            httpx_available = True
        except ImportError:
            httpx = None  # type: ignore[misc,assignment]
            httpx_available = False

        api_key = self.api_key or os.getenv("TAVILY_API_KEY")

        if not api_key:
            # 如果没有 Tavily API Key，尝试使用 jina.ai reader
            if not httpx_available or httpx is None:
                return "Error: httpx not installed. Run: uv add httpx"
            return self._extract_with_jina(urls, httpx)

        if not httpx_available or httpx is None:
            return "Error: httpx not installed. Run: uv add httpx"

        try:
            response = httpx.post(
                "https://api.tavily.com/extract",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "urls": urls,
                    "extract_depth": self.extract_depth,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return self._format_results(data)

        except httpx.HTTPStatusError as e:
            return f"Extract failed: {e.response.status_code}"
        except httpx.TimeoutException:
            return t("errors.timeout")
        except Exception as e:
            return f"{t('errors.generic')}: {str(e)}"

    def _extract_with_jina(self, urls: list[str], httpx: Any) -> str:
        """使用 jina.ai reader 提取网页内容（无需 API Key）.
        
        Args:
            urls: URL 列表.
            httpx: httpx 模块.
            
        Returns:
            提取的内容字符串.
        """
        if not httpx:
             return "Error: httpx not installed. Run: uv add httpx"
             
        output_parts = []
        failed_urls = []
        
        for url in urls:
            try:
                # 使用 jina.ai reader: https://r.jina.ai/<url>
                jina_url = f"https://r.jina.ai/{url}"
                response = httpx.get(jina_url, timeout=30.0)
                
                if response.status_code == 200:
                    output_parts.append(f"## {url}\n")
                    content = response.text
                    truncated = content[:5000] + "..." if len(content) > 5000 else content
                    output_parts.append(truncated)
                    output_parts.append("\n---\n")
                else:
                    failed_urls.append(url)
                    
            except Exception:
                failed_urls.append(url)
                
        if failed_urls:
            output_parts.append(f"\n**Failed URLs**: {', '.join(failed_urls)}")
            
        return "\n".join(output_parts) if output_parts else "No content extracted (Jina)"

    def _format_results(self, data: dict[str, Any]) -> str:
        """格式化提取结果.

        Args:
            data: API 返回的数据。

        Returns:
            格式化后的结果字符串。
        """
        results = data.get("results", [])
        failed = data.get("failed_results", [])

        output_parts = []

        for result in results:
            url = result.get("url", "")
            raw_content = result.get("raw_content", "")
            output_parts.append(f"## {url}\n")
            truncated = raw_content[:5000] + "..." if len(raw_content) > 5000 else raw_content
            output_parts.append(truncated)
            output_parts.append("\n---\n")

        if failed:
            failed_urls = [f.get("url", "unknown") for f in failed]
            output_parts.append(f"\n**Failed URLs**: {', '.join(failed_urls)}")

        return "\n".join(output_parts) if output_parts else "No content extracted"
