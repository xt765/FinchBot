"""会话标题工具.

提供 Agent 获取和修改会话标题的能力，以及 AI 生成会话标题的函数。
"""

from pathlib import Path
from typing import Any

from pydantic import Field

from finchbot.i18n import t
from finchbot.sessions import SessionMetadataStore
from finchbot.tools.base import FinchTool


def generate_session_title_with_ai(
    chat_model,
    messages: list,
) -> str | None:
    """使用 AI 分析对话内容生成会话标题.

    Args:
        chat_model: 聊天模型实例
        messages: 对话消息列表

    Returns:
        生成的标题，如果失败则返回 None
    """
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        conversation = []
        for msg in messages[-4:]:
            if hasattr(msg, "type") and hasattr(msg, "content"):
                role = "用户" if msg.type == "human" else "AI"
                content = msg.content[:100]
                conversation.append(f"{role}: {content}")

        conversation_text = "\n".join(conversation)

        system_prompt = (
            "你是一个会话标题生成助手。请根据以下对话内容，"
            "生成一个简洁的标题（不超过十五个字符）。\n\n"
            "要求：\n"
            "1. 标题要准确概括对话主题\n"
            "2. 不要包含标点符号\n"
            "3. 长度控制在 5-15 个字符\n\n"
            "请直接输出标题，不要添加任何解释。"
        )

        user_prompt = f"请为以下对话生成标题：\n\n{conversation_text}"

        response = chat_model.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        title = response.content.strip()

        if 5 <= len(title) <= 15:
            return title
        return None

    except Exception as e:
        from loguru import logger

        logger.warning(f"Failed to generate session title with AI: {e}")
        return None


class SessionTitleTool(FinchTool):
    """会话标题工具.

    用于获取和修改当前会话的标题。
    """

    name: str = Field(default="session_title", description="Tool name")
    description: str = Field(default="", description="Tool description")
    workspace: str = Field(default="", exclude=True)
    session_id: str = Field(default="", exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        desc = t("tools.session_title.description")
        hint = t("tools.session_title.hint")
        self.description = f"{desc} {hint}" if hint != "tools.session_title.hint" else desc

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": t("tools.session_title.param_action"),
                    "enum": ["get", "set"],
                },
                "title": {
                    "type": "string",
                    "description": t("tools.session_title.param_title"),
                },
            },
            "required": ["action"],
        }

    def _run(self, action: str, title: str | None = None) -> str:
        """执行会话标题操作.

        Args:
            action: 操作类型，get 或 set
            title: 新标题（仅 set 时需要）

        Returns:
            操作结果消息
        """
        try:
            workspace = (
                Path(self.workspace) if self.workspace else Path.home() / ".finchbot" / "workspace"
            )
            session_store = SessionMetadataStore(workspace)

            if action == "get":
                return self._get_title(session_store)
            if action == "set":
                if not title:
                    return t("tools.session_title.error_no_title")
                return self._set_title(session_store, title)
            return t("tools.session_title.error_invalid_action")
        except Exception as e:
            from loguru import logger

            logger.warning(f"SessionTitleTool error: {e}")
            return f"Error: {str(e)}"

    def _get_title(self, session_store: SessionMetadataStore) -> str:
        """获取当前会话标题.

        Args:
            session_store: 会话存储实例

        Returns:
            当前标题信息
        """
        session = session_store.get_session(self.session_id)
        if session is None:
            return t("tools.session_title.no_session")

        current_title = session.title
        needs_title = not current_title.strip() or current_title == self.session_id

        if needs_title:
            return t("tools.session_title.current_none").format(
                session_id=self.session_id,
                hint=t("tools.session_title.get_hint"),
            )

        return t("tools.session_title.current").format(
            title=current_title,
            message_count=session.message_count,
        )

    def _set_title(self, session_store: SessionMetadataStore, title: str) -> str:
        """设置会话标题.

        Args:
            session_store: 会话存储实例
            title: 新标题

        Returns:
            设置结果消息
        """
        title = title.strip()

        session = session_store.get_session(self.session_id)
        if session is None:
            session_store.create_session(
                session_id=self.session_id,
                title=title,
                message_count=0,
            )
            return t("tools.session_title.set_success").format(title=title)

        session_store.update_activity(
            self.session_id, title=title, message_count=session.message_count
        )
        return t("tools.session_title.set_success").format(title=title)
