"""Conversation and message persistence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Conversation, Message


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, limit: int = 50, offset: int = 0) -> list[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def create(self, title: str, model_name: str | None = None) -> Conversation:
        conversation = Conversation(title=title, model_name=model_name)
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        *,
        model_name: str | None = None,
        activities: list[dict[str, Any]] | None = None,
        sources: list[dict[str, Any]] | None = None,
        memory_used: int = 0,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_name=model_name,
            activities=activities or [],
            sources=sources or [],
            memory_used=memory_used,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def rename(self, conversation_id: uuid.UUID, title: str) -> Conversation | None:
        conversation = await self.get(conversation_id)
        if conversation is None:
            return None
        conversation.title = title
        await self._session.flush()
        return conversation

    async def delete(self, conversation_id: uuid.UUID) -> bool:
        conversation = await self.get(conversation_id)
        if conversation is None:
            return False
        await self._session.delete(conversation)
        return True
