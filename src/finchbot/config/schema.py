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
    """

    language: str = "en-US"
    language_set_by_user: bool = False
    default_model: str = "gpt-5"
    default_model_set_by_user: bool = False
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)

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
