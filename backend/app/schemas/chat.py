"""
Chat and Message Pydantic schemas.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------- Message Schemas ----------

class MessageCreate(BaseModel):
    """Schema for sending a new message."""
    content: str
    mode: str = "general"  # "general", "coding", "image"

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message content cannot be empty")
        if len(v) > 10000:
            raise ValueError("Message content too long (max 10,000 characters)")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        v = v.strip().lower()
        allowed = {"general", "coding", "image"}
        if v not in allowed:
            raise ValueError(f"Invalid mode. Must be one of: {', '.join(allowed)}")
        return v


class MessageResponse(BaseModel):
    """Schema for returning a message."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    role: str
    content: str
    mode: str
    image_url: Optional[str] = None
    timestamp: datetime


# ---------- Chat Schemas ----------

class ChatCreate(BaseModel):
    """Schema for creating a new chat."""
    title: Optional[str] = "New Chat"

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> str:
        title = (value or "New Chat").strip()
        if len(title) > 255:
            raise ValueError("Chat title too long (max 255 characters)")
        return title or "New Chat"


class ChatResponse(BaseModel):
    """Schema for returning a chat (without messages)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime


class ChatDetailResponse(BaseModel):
    """Schema for returning a chat with all messages."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)


class SendMessageResponse(BaseModel):
    """Schema for the response when sending a message — returns both user and AI messages."""
    user_message: MessageResponse
    ai_message: MessageResponse
