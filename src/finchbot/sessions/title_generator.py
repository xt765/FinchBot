"""会话标题生成器.

使用 AI 分析对话内容，自动生成简洁的会话标题。
"""

from collections.abc import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from loguru import logger

MAX_MESSAGES_TO_ANALYZE = 4  # 只分析最近 4 条消息，减少 token 消耗
MAX_CONTENT_PREVIEW_LENGTH = 100  # 每条消息截取前 100 字符


def generate_session_title_with_ai(
    chat_model: BaseChatModel,
    messages: Sequence[BaseMessage],
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

        from finchbot.i18n import t

        conversation = []
        for msg in messages[-MAX_MESSAGES_TO_ANALYZE:]:
            if hasattr(msg, "type") and hasattr(msg, "content"):
                role = (
                    t("session_title.role_user")
                    if msg.type == "human"
                    else t("session_title.role_ai")
                )
                content = msg.content[:MAX_CONTENT_PREVIEW_LENGTH]
                conversation.append(f"{role}: {content}")

        conversation_text = "\n".join(conversation)

        system_prompt = t("session_title.prompt_system")
        user_prompt = t("session_title.prompt_user", conversation=conversation_text)

        response = chat_model.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        content = response.content
        if isinstance(content, str):
            return content.strip()
        return None

    except Exception as e:
        logger.warning(f"AI 会话标题生成失败: {e}")
        return None
