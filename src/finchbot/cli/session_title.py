"""会话标题生成模块.

提供基于 AI 和简单规则生成会话标题的功能.
"""

from __future__ import annotations

import re

from loguru import logger


def _generate_session_title_with_ai(
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
            "2. 使用中文\n"
            "3. 不要包含标点符号\n"
            "4. 长度控制在 5-15 个字符\n\n"
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

        title = re.sub(r'["\'""' r"，。？！,.?!\s]+", "", title)

        if len(title) > 15:
            title = title[:15]

        return title if title else None

    except Exception as e:
        logger.warning(f"Failed to generate session title with AI: {e}")
        return None


def _generate_session_title_simple(first_message: str, max_length: int = 20) -> str:
    """根据第一条消息生成会话标题（简单版本，作为备选）.

    Args:
        first_message: 用户的第一条消息
        max_length: 标题最大长度

    Returns:
        生成的标题
    """
    prefixes = ["请", "帮我", "我想", "我要", "能不能", "可以", "请问"]
    content = first_message.strip()
    for prefix in prefixes:
        if content.startswith(prefix):
            content = content[len(prefix) :].strip()
            break

    content = re.sub(r"[，。？！,.?!\"'\s]+", " ", content).strip()

    if len(content) <= max_length:
        return content if content else "新会话"

    truncated = content[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated.strip() + "..."
