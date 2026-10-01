"""Conversation endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session_required
from app.core.errors import NotFoundError, ValidationError
from app.db.repositories.conversations import ConversationRepository
from app.schemas import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _to_out(conversation) -> ConversationOut:
    return ConversationOut(
        id=str(conversation.id),
        title=conversation.title,
        model=conversation.model_name,
        createdAt=conversation.created_at.isoformat() if conversation.created_at else "",
        updatedAt=conversation.updated_at.isoformat() if conversation.updated_at else "",
    )


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session_required),
) -> list[ConversationOut]:
    conversations = await ConversationRepository(session).list(limit=limit, offset=offset)
    return [_to_out(c) for c in conversations]


@router.post("", response_model=ConversationOut)
async def create_conversation(
    body: ConversationCreate,
    session: AsyncSession = Depends(get_session_required),
) -> ConversationOut:
    conversation = await ConversationRepository(session).create(
        title=body.title or "New conversation", model_name=body.model
    )
    return _to_out(conversation)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session_required),
) -> ConversationDetailOut:
    conversation = await ConversationRepository(session).get(conversation_id)
    if conversation is None:
        raise NotFoundError(f"Conversation not found: {conversation_id}")
    detail = ConversationDetailOut(
        **_to_out(conversation).model_dump(),
        messages=[
            MessageOut(
                id=str(m.id),
                role=m.role,
                content=m.content,
                timestamp=m.created_at.isoformat() if m.created_at else "",
                model=m.model_name,
                activities=m.activities or [],
                sources=m.sources or [],
                memoryUsed=m.memory_used,
            )
            for m in conversation.messages
        ],
    )
    return detail


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    session: AsyncSession = Depends(get_session_required),
) -> ConversationOut:
    """Rename a conversation (used by the chat history sidebar)."""
    title = body.title.strip()
    if not title:
        raise ValidationError("Title must not be empty")
    conversation = await ConversationRepository(session).rename(conversation_id, title)
    if conversation is None:
        raise NotFoundError(f"Conversation not found: {conversation_id}")
    return _to_out(conversation)


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session_required),
) -> dict[str, object]:
    deleted = await ConversationRepository(session).delete(conversation_id)
    if not deleted:
        raise NotFoundError(f"Conversation not found: {conversation_id}")
    return {"ok": True}
