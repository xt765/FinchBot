"""ConfigureMCPTool 单元测试."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from finchbot.config.schema import MCPServerConfig
from finchbot.tools.config_tools import ConfigureMCPTool


@pytest.fixture
def temp_workspace():
    """创建临时工作目录."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        config_dir = workspace / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield workspace


@pytest.fixture
def tool(temp_workspace):
    """创建工具实例."""
    return ConfigureMCPTool(workspace=str(temp_workspace))


class TestConfigureMCPTool:
    """ConfigureMCPTool 测试类."""

    def test_add_server(self, tool: ConfigureMCPTool, temp_workspace: Path):
        """测试添加 MCP 服务器."""
        result = tool._run(
            action="add",
            server_name="test-server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-test"],
            env={"API_KEY": "test-key"},
        )

        assert "added successfully" in result

        mcp_path = temp_workspace / "config" / "mcp.json"
        assert mcp_path.exists()

        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert "test-server" in data["servers"]
        assert data["servers"]["test-server"]["command"] == "npx"

    def test_update_server(self, tool: ConfigureMCPTool, temp_workspace: Path):
        """测试更新 MCP 服务器."""
        tool._run(
            action="add",
            server_name="test-server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-test"],
        )

        result = tool._run(
            action="update",
            server_name="test-server",
            command="uvx",
        )

        assert "updated successfully" in result

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert data["servers"]["test-server"]["command"] == "uvx"

    def test_remove_server(self, tool: ConfigureMCPTool, temp_workspace: Path):
        """测试删除 MCP 服务器."""
        tool._run(
            action="add",
            server_name="test-server",
            command="npx",
        )

        result = tool._run(
            action="remove",
            server_name="test-server",
        )

        assert "removed successfully" in result

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert "test-server" not in data["servers"]

    def test_list_servers(self, tool: ConfigureMCPTool):
        """测试列出 MCP 服务器."""
        tool._run(
            action="add",
            server_name="server1",
            command="npx",
        )
        tool._run(
            action="add",
            server_name="server2",
            command="uvx",
        )

        result = tool._run(action="list")

        assert "server1" in result
        assert "server2" in result

    def test_enable_server(self, tool: ConfigureMCPTool, temp_workspace: Path):
        """测试启用 MCP 服务器."""
        tool._run(
            action="add",
            server_name="test-server",
            command="npx",
        )

        tool._run(
            action="disable",
            server_name="test-server",
        )

        result = tool._run(
            action="enable",
            server_name="test-server",
        )

        assert "enabled successfully" in result

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert data["servers"]["test-server"]["disabled"] is False

    def test_disable_server(self, tool: ConfigureMCPTool, temp_workspace: Path):
        """测试禁用 MCP 服务器."""
        tool._run(
            action="add",
            server_name="test-server",
            command="npx",
        )

        result = tool._run(
            action="disable",
            server_name="test-server",
        )

        assert "disabled successfully" in result

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert data["servers"]["test-server"]["disabled"] is True

    def test_enable_nonexistent_server(self, tool: ConfigureMCPTool):
        """测试启用不存在的服务器."""
        result = tool._run(
            action="enable",
            server_name="nonexistent",
        )

        assert "not found" in result

    def test_disable_nonexistent_server(self, tool: ConfigureMCPTool):
        """测试禁用不存在的服务器."""
        result = tool._run(
            action="disable",
            server_name="nonexistent",
        )

        assert "not found" in result

    def test_remove_nonexistent_server(self, tool: ConfigureMCPTool):
        """测试删除不存在的服务器."""
        result = tool._run(
            action="remove",
            server_name="nonexistent",
        )

        assert "not found" in result

    def test_toggle_preserves_other_config(
        self, tool: ConfigureMCPTool, temp_workspace: Path
    ):
        """测试启用/禁用操作保留其他配置."""
        tool._run(
            action="add",
            server_name="test-server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-test"],
            env={"API_KEY": "test-key"},
        )

        tool._run(
            action="disable",
            server_name="test-server",
        )

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        server = data["servers"]["test-server"]

        assert server["command"] == "npx"
        assert server["args"] == ["-y", "@modelcontextprotocol/server-test"]
        assert server["env"]["API_KEY"] == "test-key"
        assert server["disabled"] is True

        tool._run(
            action="enable",
            server_name="test-server",
        )

        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        server = data["servers"]["test-server"]

        assert server["command"] == "npx"
        assert server["args"] == ["-y", "@modelcontextprotocol/server-test"]
        assert server["env"]["API_KEY"] == "test-key"
        assert server["disabled"] is False

    def test_list_shows_disabled_status(self, tool: ConfigureMCPTool):
        """测试列表显示禁用状态."""
        tool._run(
            action="add",
            server_name="enabled-server",
            command="npx",
        )
        tool._run(
            action="add",
            server_name="disabled-server",
            command="npx",
        )
        tool._run(
            action="disable",
            server_name="disabled-server",
        )

        result = tool._run(action="list")

        assert "enabled-server" in result
        assert "disabled-server" in result
        assert "disabled" in result
