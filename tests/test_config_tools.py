"""ConfigureMCP 工具单元测试."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from finchbot.tools.builtin import config as config_module


@pytest.fixture
def temp_workspace():
    """创建临时工作目录."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        config_dir = workspace / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield workspace


@pytest.fixture(autouse=True)
def setup_config(temp_workspace: Path):
    """设置配置工具."""
    config_module.configure_config_tools(temp_workspace)


class TestConfigureMCPTool:
    """ConfigureMCP 测试类."""

    def test_add_server(self, temp_workspace: Path):
        """测试添加 MCP 服务器."""
        result, needs_reload = config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="test-server",
            command="npx",
            command_args=["-y", "@modelcontextprotocol/server-test"],
            env={"API_KEY": "test-key"},
            url=None,
        )

        assert "added successfully" in result
        assert needs_reload is True

        mcp_path = temp_workspace / "config" / "mcp.json"
        assert mcp_path.exists()

        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert "test-server" in data["servers"]
        assert data["servers"]["test-server"]["command"] == "npx"

    def test_update_server(self, temp_workspace: Path):
        """测试更新 MCP 服务器."""
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="test-server",
            command="npx",
            command_args=["-y", "@modelcontextprotocol/server-test"],
            env=None,
            url=None,
        )

        result, needs_reload = config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="test-server",
            command="uvx",
            command_args=None,
            env=None,
            url=None,
        )

        assert "updated successfully" in result
        assert needs_reload is True

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert data["servers"]["test-server"]["command"] == "uvx"

    def test_remove_server(self, temp_workspace: Path):
        """测试删除 MCP 服务器."""
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="test-server",
            command="npx",
            command_args=None,
            env=None,
            url=None,
        )

        result, needs_reload = config_module._remove_server(temp_workspace, "test-server")

        assert "removed successfully" in result
        assert needs_reload is True

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert "test-server" not in data["servers"]

    def test_list_servers(self, temp_workspace: Path):
        """测试列出 MCP 服务器."""
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="server1",
            command="npx",
            command_args=None,
            env=None,
            url=None,
        )
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="server2",
            command="uvx",
            command_args=None,
            env=None,
            url=None,
        )

        result = config_module._list_servers(temp_workspace)

        assert "server1" in result
        assert "server2" in result

    def test_enable_server(self, temp_workspace: Path):
        """测试启用 MCP 服务器."""
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="test-server",
            command="npx",
            command_args=None,
            env=None,
            url=None,
        )

        config_module._toggle_server(temp_workspace, "test-server", disabled=True)

        result, needs_reload = config_module._toggle_server(
            temp_workspace, "test-server", disabled=False
        )

        assert "enabled successfully" in result
        assert needs_reload is True

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert data["servers"]["test-server"]["disabled"] is False

    def test_disable_server(self, temp_workspace: Path):
        """测试禁用 MCP 服务器."""
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="test-server",
            command="npx",
            command_args=None,
            env=None,
            url=None,
        )

        result, needs_reload = config_module._toggle_server(
            temp_workspace, "test-server", disabled=True
        )

        assert "disabled successfully" in result
        assert needs_reload is True

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert data["servers"]["test-server"]["disabled"] is True

    def test_enable_nonexistent_server(self, temp_workspace: Path):
        """测试启用不存在的服务器."""
        result, needs_reload = config_module._toggle_server(
            temp_workspace, "nonexistent", disabled=False
        )

        assert "not found" in result
        assert needs_reload is False

    def test_disable_nonexistent_server(self, temp_workspace: Path):
        """测试禁用不存在的服务器."""
        result, needs_reload = config_module._toggle_server(
            temp_workspace, "nonexistent", disabled=True
        )

        assert "not found" in result
        assert needs_reload is False

    def test_remove_nonexistent_server(self, temp_workspace: Path):
        """测试删除不存在的服务器."""
        result, needs_reload = config_module._remove_server(temp_workspace, "nonexistent")

        assert "not found" in result
        assert needs_reload is False

    def test_toggle_preserves_other_config(self, temp_workspace: Path):
        """测试启用/禁用操作保留其他配置."""
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="test-server",
            command="npx",
            command_args=["-y", "@modelcontextprotocol/server-test"],
            env={"API_KEY": "test-key"},
            url=None,
        )

        config_module._toggle_server(temp_workspace, "test-server", disabled=True)

        mcp_path = temp_workspace / "config" / "mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        server = data["servers"]["test-server"]

        assert server["command"] == "npx"
        assert server["args"] == ["-y", "@modelcontextprotocol/server-test"]
        assert server["env"]["API_KEY"] == "test-key"
        assert server["disabled"] is True

        config_module._toggle_server(temp_workspace, "test-server", disabled=False)

        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        server = data["servers"]["test-server"]

        assert server["command"] == "npx"
        assert server["args"] == ["-y", "@modelcontextprotocol/server-test"]
        assert server["env"]["API_KEY"] == "test-key"
        assert server["disabled"] is False

    def test_list_shows_disabled_status(self, temp_workspace: Path):
        """测试列表显示禁用状态."""
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="enabled-server",
            command="npx",
            command_args=None,
            env=None,
            url=None,
        )
        config_module._add_or_update_server(
            workspace=temp_workspace,
            server_name="disabled-server",
            command="npx",
            command_args=None,
            env=None,
            url=None,
        )
        config_module._toggle_server(temp_workspace, "disabled-server", disabled=True)

        result = config_module._list_servers(temp_workspace)

        assert "enabled-server" in result
        assert "disabled-server" in result
        assert "disabled" in result
