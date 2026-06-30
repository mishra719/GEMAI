"""
Chat API endpoints — CRUD operations and message handling.
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message
from app.schemas.chat import (
    ChatCreate,
    ChatResponse,
    ChatDetailResponse,
    MessageCreate,
    MessageResponse,
    SendMessageResponse,
)
from app.services.gemini import general_chat, coding_chat, image_chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chats", tags=["Chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat."""
    chat = Chat(user_id=current_user.id, title=payload.title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    logger.info(f"Chat created: {chat.id} for user {current_user.id}")
    return chat


@router.get("", response_model=list[ChatResponse])
def list_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all chats for the current user."""
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(Chat.created_at.desc())
        .all()
    )
    return chats


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific chat with all messages."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id, Chat.user_id == current_user.id
    ).first()

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
        )

    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat and all its messages."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id, Chat.user_id == current_user.id
    ).first()

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
        )

    db.delete(chat)
    db.commit()
    logger.info(f"Chat deleted: {chat_id}")


@router.post("/{chat_id}/messages", response_model=SendMessageResponse)
async def send_message(
    chat_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and get AI response. Returns both user and AI messages."""
    # Verify chat ownership
    chat = db.query(Chat).filter(
        Chat.id == chat_id, Chat.user_id == current_user.id
    ).first()

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
        )

    # Save user message
    user_msg = Message(
        chat_id=chat_id,
        role="user",
        content=payload.content,
        mode=payload.mode,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Update chat title from first message
    msg_count = db.query(Message).filter(Message.chat_id == chat_id).count()
    if msg_count == 1:
        chat.title = payload.content[:50] + ("..." if len(payload.content) > 50 else "")
        db.commit()

    # Build conversation history for context
    previous_messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.timestamp)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in previous_messages[:-1]]

    # Route to appropriate AI handler
    ai_response = ""
    image_url = None

    try:
        if payload.mode == "coding":
            ai_response = await coding_chat(history, payload.content)
        elif payload.mode == "image":
            result = await image_chat(payload.content)
            ai_response = result.get("content", "Image generation failed.")
            image_url = result.get("image_url")  # Will be set if real image was generated
        else:
            ai_response = await general_chat(history, payload.content)
    except Exception as e:
        logger.error(f"AI service error: {e}")
        ai_response = "I'm sorry, I encountered an error. Please try again."

    # Save AI response
    ai_msg = Message(
        chat_id=chat_id,
        role="assistant",
        content=ai_response,
        mode=payload.mode,
        image_url=image_url,
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    # Return both messages
    return SendMessageResponse(
        user_message=MessageResponse(
            id=user_msg.id,
            chat_id=user_msg.chat_id,
            role=user_msg.role,
            content=user_msg.content,
            mode=user_msg.mode,
            image_url=user_msg.image_url,
            timestamp=user_msg.timestamp,
        ),
        ai_message=MessageResponse(
            id=ai_msg.id,
            chat_id=ai_msg.chat_id,
            role=ai_msg.role,
            content=ai_msg.content,
            mode=ai_msg.mode,
            image_url=ai_msg.image_url,
            timestamp=ai_msg.timestamp,
        ),
    )
