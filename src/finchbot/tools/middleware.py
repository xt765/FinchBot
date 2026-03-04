"""动态工具 Middleware.

基于 LangChain 1.0 middleware API 实现工具热更新。

LangChain 1.0 Middleware API:
- wrap_model_call: 拦截模型调用
- wrap_tool_call: 拦截工具调用
- before_model: 模型调用前执行
- after_model: 模型调用后执行
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from loguru import logger

MIDDLEWARE_AVAILABLE = False

try:
    from langchain.agents.middleware import (
        AgentMiddleware,
        ModelRequest,
        ModelResponse,
        before_model,
        wrap_model_call,
        wrap_tool_call,
    )

    MIDDLEWARE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LangChain middleware API not available: {e}")
    AgentMiddleware = object  # type: ignore
    ModelRequest = Any  # type: ignore
    ModelResponse = Any  # type: ignore
    before_model = None  # type: ignore
    wrap_model_call = None  # type: ignore
    wrap_tool_call = None  # type: ignore

if TYPE_CHECKING:
    from finchbot.tools.core import ToolRegistry
    from finchbot.tools.mcp.hot_update import MCPHotUpdateManager


class DynamicToolMiddleware(AgentMiddleware):
    """动态工具 middleware 实现.

    在模型调用前检查配置变化，动态注入 MCP 工具。
    """

    def __init__(self, cache: Any) -> None:
        """初始化 middleware.

        Args:
            cache: DynamicToolCache 实例
        """
        super().__init__()
        self.cache = cache

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """在模型调用前动态注入工具（同步版本）."""
        if self.cache.check_config_changed():
            logger.info("检测到 MCP 配置变化，重新加载工具")
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.cache.reload())
            except RuntimeError:
                pass

        all_tools = self.cache.get_tools()
        existing_names = {t.name for t in request.tools}
        new_tools = [t for t in all_tools if t.name not in existing_names]

        if new_tools:
            request.tools = [*request.tools, *new_tools]
            logger.debug(f"动态注入 {len(new_tools)} 个工具")

        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """在模型调用前动态注入工具（异步版本）."""
        if self.cache.check_config_changed():
            logger.info("检测到 MCP 配置变化，重新加载工具")
            await self.cache.reload()

        all_tools = self.cache.get_tools()
        existing_names = {t.name for t in request.tools}
        new_tools = [t for t in all_tools if t.name not in existing_names]

        if new_tools:
            request.tools = [*request.tools, *new_tools]
            logger.debug(f"动态注入 {len(new_tools)} 个工具")

        return await handler(request)


class ToolFilterMiddleware(AgentMiddleware):
    """工具过滤 middleware 实现.

    根据配置过滤可用工具。
    """

    def __init__(self, config: Any) -> None:
        """初始化 middleware.

        Args:
            config: 配置对象
        """
        super().__init__()
        self.config = config

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """过滤工具（同步版本）."""
        enabled_tools = [t for t in request.tools if self.config.is_enabled(t.name)]
        request.tools = enabled_tools
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """过滤工具（异步版本）."""
        enabled_tools = [t for t in request.tools if self.config.is_enabled(t.name)]
        request.tools = enabled_tools
        return await handler(request)


class MCPHotUpdateMiddleware(AgentMiddleware):
    """MCP 热更新 middleware 实现.

    在每次模型调用前检查 MCP 配置是否变化，如果变化则自动执行热更新。
    """

    def __init__(
        self,
        mcp_manager: MCPHotUpdateManager,
        registry: ToolRegistry,
    ) -> None:
        """初始化 middleware.

        Args:
            mcp_manager: MCPHotUpdateManager 实例
            registry: ToolRegistry 实例
        """
        super().__init__()
        self.mcp_manager = mcp_manager
        self.registry = registry

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """在模型调用前检查并执行 MCP 热更新（同步版本）."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            new_tools = loop.run_until_complete(self.mcp_manager.check_and_update())
        except RuntimeError:
            new_tools = None

        if new_tools is not None:
            self._update_request_tools(request, new_tools)

        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """在模型调用前检查并执行 MCP 热更新（异步版本）."""
        new_tools = await self.mcp_manager.check_and_update()

        if new_tools is not None:
            self._update_request_tools(request, new_tools)

        return await handler(request)

    def _update_request_tools(
        self,
        request: ModelRequest,
        new_tools: list[Any],
    ) -> None:
        """更新请求中的工具列表.

        Args:
            request: 模型请求
            new_tools: 新的工具列表
        """
        existing_names = {t.name for t in request.tools}
        added_tools = [t for t in new_tools if t.name not in existing_names]
        registry_tools = self.registry.get_tools()
        removed_names = existing_names - {t.name for t in registry_tools}

        request.tools = [t for t in request.tools if t.name not in removed_names]
        request.tools = [*request.tools, *added_tools]

        logger.info(f"MCP 热更新生效: +{len(added_tools)} 工具, -{len(removed_names)} 工具")


def create_dynamic_tool_middleware(cache: Any) -> Any:
    """创建动态工具 middleware.

    在模型调用前检查配置变化，动态注入 MCP 工具。

    Args:
        cache: DynamicToolCache 实例

    Returns:
        Middleware 对象
    """
    if not MIDDLEWARE_AVAILABLE:
        logger.warning("Middleware API 不可用，返回空 middleware")
        return None
    return DynamicToolMiddleware(cache)


def create_tool_filter_middleware(config: Any) -> Any:
    """创建工具过滤 middleware.

    根据配置过滤可用工具。

    Args:
        config: 配置对象

    Returns:
        Middleware 对象
    """
    if not MIDDLEWARE_AVAILABLE:
        logger.warning("Middleware API 不可用，返回空 middleware")
        return None
    return ToolFilterMiddleware(config)


def create_mcp_hot_update_middleware(
    mcp_manager: MCPHotUpdateManager,
    registry: ToolRegistry,
) -> Any:
    """创建 MCP 热更新 Middleware.

    在每次模型调用前检查 MCP 配置是否变化，
    如果变化则自动执行热更新。

    Args:
        mcp_manager: MCPHotUpdateManager 实例
        registry: ToolRegistry 实例

    Returns:
        Middleware 对象
    """
    if not MIDDLEWARE_AVAILABLE:
        logger.warning("Middleware API 不可用，返回空 middleware")
        return None
    return MCPHotUpdateMiddleware(mcp_manager, registry)


def create_mcp_hot_update_middlewares(
    mcp_manager: MCPHotUpdateManager,
    registry: ToolRegistry,
) -> list[Any]:
    """创建 MCP 热更新 Middleware 列表.

    使用装饰器模式创建 middleware，更符合 LangChain 1.0 推荐方式。

    Args:
        mcp_manager: MCPHotUpdateManager 实例
        registry: ToolRegistry 实例

    Returns:
        Middleware 列表
    """
    if not MIDDLEWARE_AVAILABLE:
        logger.warning("Middleware API 不可用，返回空列表")
        return []

    @wrap_model_call
    def mcp_hot_update_wrapper(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """MCP 热更新包装器."""
        import asyncio

        try:
            asyncio.get_running_loop()
            new_tools = asyncio.ensure_future(mcp_manager.check_and_update())
        except RuntimeError:
            new_tools = None

        if new_tools is not None:
            existing_names = {t.name for t in request.tools}
            added_tools = [t for t in new_tools if t.name not in existing_names]
            registry_tools = registry.get_tools()
            removed_names = existing_names - {t.name for t in registry_tools}

            request.tools = [t for t in request.tools if t.name not in removed_names]
            request.tools = [*request.tools, *added_tools]

            logger.info(f"MCP 热更新生效: +{len(added_tools)} 工具, -{len(removed_names)} 工具")

        return handler(request)

    return [mcp_hot_update_wrapper]


def is_middleware_available() -> bool:
    """检查 Middleware API 是否可用.

    Returns:
        是否可用
    """
    return MIDDLEWARE_AVAILABLE
