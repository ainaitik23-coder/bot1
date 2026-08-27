"""
app/database/crud.py

All database read/write operations live here. Nothing outside this file
should write raw SQLAlchemy queries -- keeps DB logic in one place.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation, LLMUsage, Memory, Message, User


async def get_or_create_user(session: AsyncSession, ig_scoped_id: str, username: str | None = None) -> User:
    result = await session.execute(select(User).where(User.ig_scoped_id == ig_scoped_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(ig_scoped_id=ig_scoped_id, username=username)
        session.add(user)
        await session.flush()  # get user.id without committing yet

        # every user gets exactly one conversation row (kept simple for MVP)
        conversation = Conversation(user_id=user.id)
        session.add(conversation)
        await session.flush()
    else:
        user.last_seen = datetime.now(timezone.utc)
        if username and username != user.username:
            user.username = username

    return user


async def get_conversation_for_user(session: AsyncSession, user_id: int) -> Conversation:
    result = await session.execute(select(Conversation).where(Conversation.user_id == user_id))
    conversation = result.scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(user_id=user_id)
        session.add(conversation)
        await session.flush()
    return conversation


async def save_message(
    session: AsyncSession,
    conversation_id: int,
    direction: str,
    content: str,
    msg_type: str = "text",
    media_url: str | None = None,
    model_used: str | None = None,
    tokens_used: int | None = None,
    ig_message_id: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        direction=direction,
        content=content,
        msg_type=msg_type,
        media_url=media_url,
        model_used=model_used,
        tokens_used=tokens_used,
        ig_message_id=ig_message_id,
    )
    session.add(message)
    await session.flush()
    return message


async def get_recent_messages(session: AsyncSession, conversation_id: int, limit: int) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # oldest first, for prompt building
    return messages


async def message_exists(session: AsyncSession, ig_message_id: str) -> bool:
    """Used for webhook idempotency -- avoid processing the same event twice."""
    result = await session.execute(select(Message.id).where(Message.ig_message_id == ig_message_id))
    return result.scalar_one_or_none() is not None


async def get_memories_for_user(session: AsyncSession, user_id: int) -> list[Memory]:
    result = await session.execute(select(Memory).where(Memory.user_id == user_id))
    return list(result.scalars().all())


async def add_memory(session: AsyncSession, user_id: int, key: str, value: str) -> Memory:
    memory = Memory(user_id=user_id, key=key, value=value)
    session.add(memory)
    await session.flush()
    return memory


async def log_llm_usage(
    session: AsyncSession, provider: str, tokens: int | None, success: bool, error: str | None = None
) -> None:
    session.add(LLMUsage(provider=provider, tokens=tokens, success=success, error=error))
    await session.flush()
