"""FinchBot 环境变量映射定义.

定义 MCP 敏感信息的环境变量映射，
支持通过环境变量配置敏感信息，避免明文存储在配置文件中。
"""

from typing import Any

# ========================================
# MCP 敏感信息环境变量映射
# ========================================
# 格式: {server_name: {env_var_suffix: config_key}}
# 环境变量格式: FINCHBOT_MCP_{SUFFIX}
# 例如: FINCHBOT_MCP_GITHUB_TOKEN -> mcp.servers.github.env.GITHUB_PERSONAL_ACCESS_TOKEN

MCP_SENSITIVE_ENV_VARS: dict[str, dict[str, str]] = {
    "github": {
        "GITHUB_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
    },
    "brave-search": {
        "BRAVE_API_KEY": "BRAVE_API_KEY",
    },
    "slack": {
        "SLACK_BOT_TOKEN": "SLACK_BOT_TOKEN",
    },
    "google-maps": {
        "GOOGLE_MAPS_API_KEY": "GOOGLE_MAPS_API_KEY",
    },
    "postgres": {
        "POSTGRES_CONNECTION_STRING": "POSTGRES_CONNECTION_STRING",
    },
    "sqlite": {
        "SQLITE_DB_PATH": "SQLITE_DB_PATH",
    },
    "puppeteer": {},
    "fetch": {},
    "filesystem": {},
}

# ========================================
# 完整 MCP 环境变量配置前缀
# ========================================
# 格式: FINCHBOT_MCP__{SERVER_NAME}__{FIELD}
# 例如: FINCHBOT_MCP__GITHUB__COMMAND=npx

MCP_ENV_PREFIX = "FINCHBOT_MCP__"


def get_mcp_env_var(suffix: str) -> str | None:
    """获取 MCP 环境变量值.

    Args:
        suffix: 环境变量后缀，如 "GITHUB_TOKEN".

    Returns:
        环境变量值，如果未设置则返回 None.
    """
    import os

    return os.getenv(f"FINCHBOT_MCP_{suffix}")


def get_all_mcp_env_vars() -> dict[str, Any]:
    """获取所有 MCP 相关的环境变量.

    Returns:
        解析后的 MCP 配置字典.
    """
    import json
    import os

    servers: dict[str, dict[str, Any]] = {}

    for key, value in os.environ.items():
        if not key.startswith(MCP_ENV_PREFIX):
            continue

        parts = key[len(MCP_ENV_PREFIX) :].split("__")
        if len(parts) < 2:
            continue

        server_name = parts[0].lower()
        field = parts[1].lower()

        if server_name not in servers:
            servers[server_name] = {}

        if field == "command":
            servers[server_name]["command"] = value
        elif field == "args":
            try:
                servers[server_name]["args"] = json.loads(value)
            except json.JSONDecodeError:
                servers[server_name]["args"] = [value]
        elif field == "url":
            servers[server_name]["url"] = value
        elif field == "disabled":
            servers[server_name]["disabled"] = value.lower() == "true"
        elif field.startswith("env__"):
            env_key = field[5:]
            if "env" not in servers[server_name]:
                servers[server_name]["env"] = {}
            servers[server_name]["env"][env_key] = value

    return servers
