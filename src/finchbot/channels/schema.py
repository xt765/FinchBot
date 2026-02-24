from typing import Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class InboundMessage(BaseModel):
    """Message received from a chat channel."""
    channel: str
    sender_id: str
    chat_id: str
    content: str
    media: List[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def session_key(self) -> str:
        """Unique key for session identification: {channel}:{chat_id}"""
        return f"{self.channel}:{self.chat_id}"

class OutboundMessage(BaseModel):
    """Message to send to a chat channel."""
    target_channel: str
    target_id: str
    content: str
    files: List[str] = Field(default_factory=list)
    reply_to: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
