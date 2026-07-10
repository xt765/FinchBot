"""Configuration loader regression tests."""

from __future__ import annotations

import json
from pathlib import Path

from finchbot.config.env_mappings import get_all_mcp_env_vars
from finchbot.config.loader import load_mcp_config, save_mcp_config
from finchbot.config.schema import MCPServerConfig


def test_load_mcp_config_supports_headers_from_env(monkeypatch) -> None:
    """HTTP MCP headers from env should be loaded into server config."""
    monkeypatch.setenv("FINCHBOT_MCP__REMOTE__URL", "https://example.com/mcp")
    monkeypatch.setenv(
        "FINCHBOT_MCP__REMOTE__HEADERS",
        json.dumps({"Authorization": "Bearer env-token"}),
    )

    servers = load_mcp_config()

    assert servers["remote"].url == "https://example.com/mcp"
    assert servers["remote"].headers == {"Authorization": "Bearer env-token"}


def test_load_mcp_config_env_headers_override_workspace_headers(
    tmp_path: Path, monkeypatch
) -> None:
    """Env MCP headers should override headers loaded from workspace config."""
    save_mcp_config(
        {
            "remote": MCPServerConfig(
                url="https://example.com/mcp",
                headers={"Authorization": "Bearer file-token"},
            )
        },
        tmp_path,
    )
    monkeypatch.setenv(
        "FINCHBOT_MCP__REMOTE__HEADERS",
        json.dumps({"Authorization": "Bearer env-token"}),
    )

    servers = load_mcp_config(tmp_path)

    assert servers["remote"].headers == {"Authorization": "Bearer env-token"}


def test_get_all_mcp_env_vars_parses_nested_env_fields(monkeypatch) -> None:
    """Nested ENV fields should be exposed by the env mapping helper."""
    monkeypatch.setenv("FINCHBOT_MCP__GITHUB__COMMAND", "npx")
    monkeypatch.setenv("FINCHBOT_MCP__GITHUB__ENV__GITHUB_TOKEN", "secret")

    servers = get_all_mcp_env_vars()

    assert servers["github"]["command"] == "npx"
    assert servers["github"]["env"]["GITHUB_TOKEN"] == "secret"


def test_get_all_mcp_env_vars_parses_headers(monkeypatch) -> None:
    """HTTP MCP headers should be exposed by the env mapping helper."""
    monkeypatch.setenv(
        "FINCHBOT_MCP__REMOTE__HEADERS",
        json.dumps({"Authorization": "Bearer token"}),
    )

    servers = get_all_mcp_env_vars()

    assert servers["remote"]["headers"] == {"Authorization": "Bearer token"}
