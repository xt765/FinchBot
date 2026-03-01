"""FinchBot 工具基类.

基于 LangChain BaseTool 实现，提供统一的工具接口。
参考 Nanobot 的 Tool 设计，增强验证和错误处理。
"""

from __future__ import annotations

import inspect
import warnings
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from langchain_core.utils.pydantic import _create_subset_model, get_fields
from loguru import logger
from pydantic import Field, validate_arguments
from pydantic.warnings import PydanticDeprecationWarning


class FinchTool(BaseTool):
    """FinchBot 工具基类.

    继承 LangChain BaseTool，提供统一的工具接口。
    所有 FinchBot 工具都应继承此类。

    Attributes:
        name: 工具名称，用于函数调用。
        description: 工具描述，说明工具功能。
        parameters: 工具参数定义（可选）。
        allowed_dirs: 允许访问的目录列表（可选）。
        workspace: 工作目录路径（可选）。
    """

    name: str = Field(default="", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)

    allowed_dirs: list[Path] | None = None

    @property
    def parameters(self) -> dict[str, Any]:
        """返回工具参数定义.

        子类可以覆写此属性以提供自定义参数定义。
        """
        return {}

    def get_input_schema(self, config: Any = None) -> Any:
        """获取输入 schema，修复 LangChain 的 v__args bug.

        LangChain 的 create_schema_from_function 函数在处理名为 'args' 或 'kwargs'
        的参数时存在两个问题：
        1. Pydantic 会创建内部字段 v__args/v__kwargs，但 LangChain 没有过滤
        2. LangChain 会错误地过滤掉名为 'args' 的普通参数（即使不是 *args）

        此方法修复这两个问题。

        Args:
            config: Runnable 配置（可选）。

        Returns:
            输入 schema（Pydantic BaseModel）。
        """
        if self.args_schema is not None:
            return self.args_schema

        # 自己实现 schema 生成，避免 LangChain 的 bug
        sig = inspect.signature(self._run)

        # 检查是否有 VAR_POSITIONAL 或 VAR_KEYWORD 参数
        has_var_args = any(p.kind == p.VAR_POSITIONAL for p in sig.parameters.values())
        has_var_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())

        # 使用 Pydantic validate_arguments
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=PydanticDeprecationWarning)
            validated = validate_arguments(self._run)  # type: ignore[misc]

        inferred_model = validated.model

        # 过滤字段
        internal_fields = {"v__args", "v__kwargs", "v__duplicate_kwargs"}
        filtered_fields = {"self", "run_manager", "callbacks"}

        valid_fields = []
        for field in get_fields(inferred_model):
            # 过滤内部字段
            if field in internal_fields:
                continue
            # 过滤 self 和 callbacks
            if field in filtered_fields:
                continue
            # LangChain bug: 当没有 VAR_POSITIONAL 时过滤 args
            # 我们修复这个：只有当 args 不是普通参数时才过滤
            if field == "args" and not has_var_args and "args" not in sig.parameters:
                continue
            if field == "kwargs" and not has_var_kwargs and "kwargs" not in sig.parameters:
                continue
            valid_fields.append(field)

        if len(valid_fields) == len(get_fields(inferred_model)):
            return inferred_model

        return _create_subset_model(self.name, inferred_model, valid_fields)

    def validate_path(self, path: str) -> Path | None:
        """验证并解析路径.

        检查路径是否在允许的目录范围内，防止越权访问。
        支持相对路径解析为相对于 workspace 的路径。

        Args:
            path: 要验证的路径字符串。

        Returns:
            解析后的绝对路径，如果验证失败返回 None。
        """
        try:
            path_obj = Path(path).expanduser()

            if not path_obj.is_absolute() and self.workspace:
                workspace_path = Path(self.workspace).expanduser().resolve()
                resolved = (workspace_path / path_obj).resolve()
            else:
                resolved = path_obj.resolve()

            if self.allowed_dirs is None:
                return resolved

            allowed_dirs = self.allowed_dirs
            if isinstance(allowed_dirs, Path):
                allowed_dirs = [allowed_dirs]

            in_allowed = any(str(resolved).startswith(str(d.resolve())) for d in allowed_dirs)
            if not in_allowed:
                logger.warning(f"Path {path} not in allowed directories")
                return None

            return resolved
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return None

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """验证工具参数.

        Args:
            params: 工具参数字典。

        Returns:
            错误消息列表，空列表表示验证通过。
        """
        errors = []

        # 获取子类定义的 parameters 字典（如果有）
        if hasattr(self, "parameters") and isinstance(self.parameters, dict):
            parameters = self.parameters

            # 检查必需参数
            required_params = parameters.get("required", [])
            for param_name in required_params:
                if param_name not in params:
                    errors.append(f"必需参数 '{param_name}' 缺失")

            # 检查参数类型（简化验证）
            param_props = parameters.get("properties", {})
            for param_name, param_value in params.items():
                if param_name in param_props:
                    param_schema = param_props[param_name]
                    param_type = param_schema.get("type")

                    if param_type == "string" and not isinstance(param_value, str):
                        errors.append(f"参数 '{param_name}' 应为字符串类型")
                    elif param_type == "integer" and not isinstance(param_value, int):
                        errors.append(f"参数 '{param_name}' 应为整数类型")
                    elif param_type == "boolean" and not isinstance(param_value, bool):
                        errors.append(f"参数 '{param_name}' 应为布尔类型")

        if errors:
            logger.warning(f"工具 '{self.name}' 参数验证失败: {errors}")

        return errors

    def to_schema(self) -> dict[str, Any]:
        """转换为工具定义格式（兼容 OpenAI 和 LangChain）.

        Returns:
            工具定义字典。
        """
        # 尝试获取 parameters 属性，如果不存在则设为空字典
        params = getattr(self, "parameters", {})

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }

    def to_openai_schema(self) -> dict[str, Any]:
        """转换为 OpenAI 函数调用格式（兼容性方法）.

        Returns:
            OpenAI 格式的工具定义字典。
        """
        return self.to_schema()

    def __str__(self) -> str:
        """字符串表示."""
        return f"FinchTool(name='{self.name}', description='{self.description}')"

    def __repr__(self) -> str:
        """详细表示."""
        params = getattr(self, "parameters", {})
        return (
            f"FinchTool(name='{self.name}', description='{self.description}', parameters={params})"
        )
