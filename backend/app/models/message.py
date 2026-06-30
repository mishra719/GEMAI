"""
Message database model.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    mode = Column(String(20), default="general")  # "general", "coding", "image"
    image_url = Column(String(500), nullable=True)  # URL for generated images
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    chat = relationship("Chat", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', mode='{self.mode}')>"
