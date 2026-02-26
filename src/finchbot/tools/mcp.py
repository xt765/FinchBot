"""MCP (Model Context Protocol) 工具集成.

允许 FinchBot 作为 MCP Client 连接外部 MCP Server.
"""

from typing import Any

from loguru import logger


class MCPClient:
    """MCP 客户端 - 简化版."""

    def __init__(self, config: dict):
        self.servers = {}
        mcp_config = config.get("mcp", {})

        for name, server_config in mcp_config.get("servers", {}).items():
            self.servers[name] = {
                "command": server_config.get("command"),
                "args": server_config.get("args", []),
                "env": server_config.get("env"),
                "session": None
            }

    async def connect(self, name: str) -> Any:
        """连接指定 MCP Server."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            logger.error("mcp package not installed. Run: pip install mcp")
            return None

        server = self.servers.get(name)
        if not server:
            logger.error(f"MCP server '{name}' not found")
            return None

        params = StdioServerParameters(
            command=server["command"],
            args=server["args"],
            env=server["env"]
        )

        try:
            from contextlib import AsyncExitStack
            async with AsyncExitStack() as stack:
                (read, write) = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                server["session"] = session
                logger.info(f"MCP server '{name}' connected")
                return session
        except Exception as e:
            logger.error(f"Failed to connect MCP server '{name}': {e}")
            return None

    async def list_tools(self, server_name: str) -> list[dict]:
        """列出指定 Server 的可用工具."""
        session = await self.connect(server_name)
        if not session:
            return []

        try:
            tools = await session.list_tools()
            return tools
        except Exception as e:
            logger.error(f"Failed to list tools from '{server_name}': {e}")
            return []

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """调用指定 Server 的工具."""
        session = await self.connect(server_name)
        if not session:
            return None

        try:
            result = await session.call_tool(tool_name, arguments)
            logger.debug(f"MCP tool '{tool_name}' called on '{server_name}'")
            return result.content if hasattr(result, 'content') else result
        except Exception as e:
            logger.error(f"Failed to call MCP tool '{tool_name}': {e}")
            return None

    async def connect_all(self):
        """连接所有配置的 Server."""
        for name in self.servers:
            await self.connect(name)

    def get_all_tools(self) -> list[dict]:
        """获取所有 Server 的工具列表（需先连接）."""
        all_tools = []
        for name, server in self.servers.items():
            if server.get("session"):
                # 这里假设 session 有 tools 属性
                tools = getattr(server["session"], "tools", [])
                for tool in tools:
                    tool["_server"] = name
                all_tools.extend(tools)
        return all_tools


class MCPToolWrapper:
    """MCP 工具包装器 - 适配 FinchBot 工具接口."""

    def __init__(self, server_name: str, tool_name: str, tool_schema: dict, client: MCPClient):
        self.server_name = server_name
        self.tool_name = tool_name
        self.schema = tool_schema
        self.client = client
        self.name = tool_name
        self.description = tool_schema.get("description", "")
        self.parameters = tool_schema.get("parameters", {})

    async def execute(self, **kwargs) -> str:
        """执行工具."""
        result = await self.client.call_tool(self.server_name, self.tool_name, kwargs)
        if result is None:
            return f"Error: Failed to execute {self.tool_name}"
        return str(result)

    def to_openai_schema(self) -> dict:
        """转换为 OpenAI 工具格式."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
