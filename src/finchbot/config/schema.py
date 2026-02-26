"""FinchBot 配置模式定义.

使用 Pydantic 定义配置结构。
"""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentDefaults(BaseModel):
    """Agent 默认配置.

    Attributes:
        workspace: 工作目录路径。
        model: 默认使用的模型。
        max_tokens: 最大输出 token 数。
        temperature: 生成温度。
        max_tool_iterations: 最大工具调用迭代次数。
    """

    workspace: str = "~/.finchbot/workspace"
    model: str = "gpt-5"
    max_tokens: int = 8192
    temperature: float = 0.7
    max_tool_iterations: int = 20


class AgentsConfig(BaseModel):
    """Agent 配置.

    Attributes:
        defaults: 默认配置。
    """

    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class ProviderConfig(BaseModel):
    """LLM 提供商配置.

    Attributes:
        api_key: API 密钥。
        api_base: API 基础 URL。
        extra_headers: 额外的请求头。
        models: 可用模型列表（可选）。
        openai_compatible: 是否兼容 OpenAI API。
    """

    api_key: str = ""
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None
    models: list[str] | None = None
    openai_compatible: bool = True


class ProvidersConfig(BaseModel):
    """LLM 提供商配置集合.

    Attributes:
        openai: OpenAI 配置。
        anthropic: Anthropic 配置。
        openrouter: OpenRouter 配置。
        deepseek: DeepSeek 配置。
        groq: Groq 配置。
        gemini: Google Gemini 配置。
        moonshot: Moonshot/Kimi 配置。
        dashscope: DashScope/阿里云配置。
        custom: 自定义提供商配置。
    """

    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)
    groq: ProviderConfig = Field(default_factory=ProviderConfig)
    gemini: ProviderConfig = Field(default_factory=ProviderConfig)
    moonshot: ProviderConfig = Field(default_factory=ProviderConfig)
    dashscope: ProviderConfig = Field(default_factory=ProviderConfig)
    custom: dict[str, ProviderConfig] = Field(default_factory=dict)


class WebSearchConfig(BaseModel):
    """网页搜索工具配置.

    Attributes:
        api_key: Tavily API 密钥。
        brave_api_key: Brave Search API 密钥。
        max_results: 最大搜索结果数。
    """

    api_key: str = ""
    brave_api_key: str = ""
    max_results: int = 5


class WebToolsConfig(BaseModel):
    """网页工具配置.

    Attributes:
        search: 搜索配置。
    """

    search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class ExecToolConfig(BaseModel):
    """Shell 执行工具配置.

    Attributes:
        timeout: 命令超时时间（秒）。
    """

    timeout: int = 60


class ToolsConfig(BaseModel):
    """工具配置.

    Attributes:
        web: 网页工具配置。
        exec: 执行工具配置。
        restrict_to_workspace: 是否限制在工作目录内。
    """

    web: WebToolsConfig = Field(default_factory=WebToolsConfig)
    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)
    restrict_to_workspace: bool = False


class MCPServerConfig(BaseModel):
    """MCP Server 配置.

    支持 stdio 和 HTTP 两种传输方式。

    Attributes:
        command: stdio 传输的启动命令。
        args: stdio 传输的命令参数。
        env: stdio 传输的环境变量。
        url: HTTP 传输的服务器 URL。
        headers: HTTP 传输的请求头（用于认证等）。
        disabled: 是否禁用此服务器。
    """

    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    url: str = ""
    headers: dict[str, str] | None = None
    disabled: bool = False


class MCPConfig(BaseModel):
    """MCP 配置集合.

    使用 langchain-mcp-adapters 官方库加载 MCP 工具。

    Attributes:
        servers: MCP 服务器配置字典。
    """

    servers: dict[str, MCPServerConfig] = Field(default_factory=dict)


class DiscordChannelConfig(BaseModel):
    """Discord 渠道配置.

    Attributes:
        enabled: 是否启用。
        token: Bot Token。
    """

    enabled: bool = False
    token: str = ""


class FeishuChannelConfig(BaseModel):
    """飞书渠道配置.

    Attributes:
        enabled: 是否启用。
        app_id: 应用 ID。
        app_secret: 应用密钥。
    """

    enabled: bool = False
    app_id: str = ""
    app_secret: str = ""


class DingTalkChannelConfig(BaseModel):
    """钉钉渠道配置.

    Attributes:
        enabled: 是否启用。
        client_id: 客户端 ID。
        client_secret: 客户端密钥。
    """

    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""


class WeChatWorkChannelConfig(BaseModel):
    """企业微信渠道配置.

    Attributes:
        enabled: 是否启用。
        corp_id: 企业 ID。
        agent_id: 应用 ID。
        secret: 应用密钥。
    """

    enabled: bool = False
    corp_id: str = ""
    agent_id: str = ""
    secret: str = ""


class EmailChannelConfig(BaseModel):
    """邮件渠道配置.

    Attributes:
        enabled: 是否启用。
        smtp_host: SMTP 服务器地址。
        smtp_port: SMTP 端口。
        smtp_user: SMTP 用户名。
        smtp_password: SMTP 密码。
        from_address: 发件人地址。
        use_tls: 是否使用 TLS。
    """

    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = ""
    use_tls: bool = True


class ChannelsConfig(BaseModel):
    """渠道配置集合.

    注意：渠道功能已迁移到 LangBot 平台。
    LangBot 支持 QQ、微信、飞书、钉钉、Discord、Telegram、Slack 等 12+ 平台。
    请使用 LangBot 的 WebUI 配置各平台：https://langbot.app

    此配置保留用于兼容性，后续版本将移除。
    """

    discord: DiscordChannelConfig = Field(default_factory=DiscordChannelConfig)
    feishu: FeishuChannelConfig = Field(default_factory=FeishuChannelConfig)
    dingtalk: DingTalkChannelConfig = Field(default_factory=DingTalkChannelConfig)
    wechat: WeChatWorkChannelConfig = Field(default_factory=WeChatWorkChannelConfig)
    email: EmailChannelConfig = Field(default_factory=EmailChannelConfig)
    langbot_enabled: bool = False


class Config(BaseSettings):
    """FinchBot 根配置.

    Attributes:
        language: 界面语言。
        language_set_by_user: 语言是否由用户手动设置。
        default_model: 默认模型。
        default_model_set_by_user: 默认模型是否由用户手动设置。
        agents: Agent 配置。
        providers: 提供商配置。
        tools: 工具配置。
        mcp: MCP 配置。
        channels: 渠道配置。
    """

    language: str = "en-US"
    language_set_by_user: bool = False
    default_model: str = "gpt-5"
    default_model_set_by_user: bool = False
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)

    model_config = SettingsConfigDict(env_prefix="FINCHBOT_", env_nested_delimiter="__")

    def get_configured_providers(self) -> list[str]:
        """获取已配置的提供商列表.

        Returns:
            已配置 API Key 的提供商名称列表。
        """
        configured = []
        preset_providers = [
            "openai",
            "anthropic",
            "openrouter",
            "deepseek",
            "groq",
            "gemini",
            "moonshot",
            "dashscope",
        ]

        for name in preset_providers:
            provider: ProviderConfig | None = getattr(self.providers, name, None)
            if provider and provider.api_key:
                configured.append(name)

        for name in self.providers.custom:
            configured.append(f"custom:{name}")

        return configured
