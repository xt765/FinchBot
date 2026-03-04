"""动态工具 Middleware.

基于 LangChain 1.0 middleware API 实现工具热更新。

LangChain 1.0 Middleware API:
- wrap_model_call: 拦截模型调用
- wrap_tool_call: 拦截工具调用
- before_model: 模型调用前执行
- after_model: 模型调用后执行
- dynamic_prompt: 动态生成系统提示词
"""

from __future__ import annotations

import platform
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

MIDDLEWARE_AVAILABLE = False
DYNAMIC_PROMPT_AVAILABLE = False

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

try:
    from langchain.agents.middleware import dynamic_prompt

    DYNAMIC_PROMPT_AVAILABLE = True
except ImportError:
    dynamic_prompt = None  # type: ignore

if TYPE_CHECKING:
    from finchbot.tools.core import ToolRegistry
    from finchbot.tools.mcp.hot_update import MCPHotUpdateManager


def _get_workspace_from_request(request: ModelRequest) -> Path:
    """从请求中获取工作目录."""
    if hasattr(request, 'runtime') and hasattr(request.runtime, 'context'):
        context = request.runtime.context
        if hasattr(context, 'workspace'):
            return Path(context.workspace)

    from finchbot.agent.core import get_default_workspace
    return get_default_workspace()


def _build_dynamic_system_prompt(request: ModelRequest) -> str:
    """构建动态系统提示词.

    包含所有需要动态更新的部分：
    1. Bootstrap 文件
    2. 技能系统
    3. 当前时间
    4. 工具文档（包含 MCP 工具）
    5. 能力信息
    """
    from finchbot.agent.capabilities import build_capabilities_prompt
    from finchbot.agent.context import ContextBuilder
    from finchbot.config import load_config
    from finchbot.config.loader import load_mcp_config
    from finchbot.tools.core import ToolRegistry
    from finchbot.tools.tools_generator import ToolsGenerator

    parts = []

    workspace = _get_workspace_from_request(request)

    context_builder = ContextBuilder(workspace)
    bootstrap_and_skills = context_builder.build_system_prompt(use_cache=False)
    if bootstrap_and_skills:
        parts.append(bootstrap_and_skills)

    now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
    parts.append(f"## 当前时间\n{now}")

    system_name = platform.system()
    if system_name == "Windows":
        platform_hint = "Windows (请使用 Windows/PowerShell 命令语法)"
    elif system_name == "Darwin":
        platform_hint = "macOS (请使用 Unix/BSD 命令语法)"
    else:
        platform_hint = f"{system_name} (请使用 Unix/Linux 命令语法)"

    runtime = f"{platform_hint}, Python {platform.python_version()}"
    parts.append(f"## 运行环境\n{runtime}")
    parts.append(f"## 工作目录\n{workspace}")

    registry = ToolRegistry.get_instance()
    all_tools = registry.get_tools() if registry else []

    tools_generator = ToolsGenerator(workspace, all_tools)
    tools_content = tools_generator.generate_tools_content()
    if tools_content:
        parts.append(tools_content)

    config = load_config()
    mcp_servers = load_mcp_config(workspace)
    if mcp_servers:
        config.mcp.servers = mcp_servers

    capabilities_prompt = build_capabilities_prompt(config, all_tools)
    if capabilities_prompt:
        parts.append(capabilities_prompt)

    return "\n\n".join(parts)


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
    支持运行时动态添加/移除 MCP 工具。
    """

    def __init__(
        self,
        mcp_manager: MCPHotUpdateManager,
        registry: ToolRegistry,
        initial_tools: list[BaseTool] | None = None,
    ) -> None:
        """初始化 middleware.

        Args:
            mcp_manager: MCPHotUpdateManager 实例
            registry: ToolRegistry 实例
            initial_tools: 初始工具列表（用于动态验证）
        """
        super().__init__()
        self.mcp_manager = mcp_manager
        self.registry = registry
        self._dynamic_tools: list[BaseTool] = list(initial_tools) if initial_tools else []

    @property
    def tools(self) -> list[BaseTool]:
        """返回当前所有动态工具.

        LangChain 会检查这个属性来验证工具是否有效。
        """
        return self._dynamic_tools

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """在模型调用前检查并执行 MCP 热更新（同步版本）."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            new_tools = asyncio.ensure_future(self.mcp_manager.check_and_update())
        except RuntimeError:
            new_tools = None

        if new_tools is not None:
            self._dynamic_tools = new_tools
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
            self._dynamic_tools = new_tools
            logger.info(f"动态工具列表已更新: {len(new_tools)} 个工具")
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
    initial_tools: list[BaseTool] | None = None,
) -> Any:
    """创建 MCP 热更新 Middleware.

    在每次模型调用前检查 MCP 配置是否变化，
    如果变化则自动执行热更新。

    Args:
        mcp_manager: MCPHotUpdateManager 实例
        registry: ToolRegistry 实例
        initial_tools: 初始工具列表（用于动态验证）

    Returns:
        Middleware 对象
    """
    if not MIDDLEWARE_AVAILABLE:
        logger.warning("Middleware API 不可用，返回空 middleware")
        return None
    return MCPHotUpdateMiddleware(
        mcp_manager=mcp_manager,
        registry=registry,
        initial_tools=initial_tools,
    )


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


def is_dynamic_prompt_available() -> bool:
    """检查 dynamic_prompt API 是否可用.

    Returns:
        是否可用
    """
    return DYNAMIC_PROMPT_AVAILABLE


def create_dynamic_system_prompt_middleware() -> Any:
    """创建动态系统提示词 middleware.

    使用 LangChain 1.0 的 @dynamic_prompt 装饰器，
    每次模型调用时动态生成系统提示词。

    Returns:
        Middleware 对象，如果 API 不可用返回 None
    """
    if not DYNAMIC_PROMPT_AVAILABLE or dynamic_prompt is None:
        logger.warning("dynamic_prompt API 不可用，返回空 middleware")
        return None

    @dynamic_prompt
    def dynamic_system_prompt(request: ModelRequest) -> str:
        """每次模型调用时动态生成系统提示词."""
        return _build_dynamic_system_prompt(request)

    return dynamic_system_prompt


def create_full_dynamic_middleware_stack(
    mcp_manager: MCPHotUpdateManager | None = None,
    registry: ToolRegistry | None = None,
    initial_tools: list[BaseTool] | None = None,
) -> list[Any]:
    """创建完整的动态 middleware 栈.

    包含：
    1. 动态系统提示词 middleware
    2. MCP 热更新 middleware

    Args:
        mcp_manager: MCPHotUpdateManager 实例（可选）
        registry: ToolRegistry 实例（可选）
        initial_tools: 初始工具列表（用于动态验证）

    Returns:
        Middleware 列表
    """
    middlewares = []

    dynamic_prompt_middleware = create_dynamic_system_prompt_middleware()
    if dynamic_prompt_middleware:
        middlewares.append(dynamic_prompt_middleware)
        logger.info("动态系统提示词 middleware 已启用")

    if mcp_manager and registry:
        mcp_middleware = create_mcp_hot_update_middleware(
            mcp_manager,
            registry,
            initial_tools=initial_tools,
        )
        if mcp_middleware:
            middlewares.append(mcp_middleware)

    return middlewares
