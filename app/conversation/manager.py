"""
app/conversation/manager.py

The orchestrator. This is what app/api/webhook.py calls after receiving
a message. Ties together: user lookup -> history -> memory -> prompt ->
LLM -> save -> return response text.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import LLMProviderError
from app.ai.router import llm_router
from app.config import settings
from app.conversation.memory import get_relevant_memories
from app.conversation.prompts import build_messages
from app.database import crud
from app.utils.logging import get_logger

log = get_logger("CONVERSATION")

FALLBACK_REPLY = "Aaj ke liye mera dimaag thak gaya hai 😅 kal fresh mood mein baat karte hain, bye!"


async def handle_incoming_message(
    session: AsyncSession,
    ig_scoped_id: str,
    username: str | None,
    incoming_text: str,
    ig_message_id: str | None,
) -> str:
    """
    Runs the full pipeline for one incoming DM and returns the text to send back.
    Everything is saved to the DB as we go, so even if sending to Instagram
    fails later, we don't lose the record.
    """
    user = await crud.get_or_create_user(session, ig_scoped_id, username)
    conversation = await crud.get_conversation_for_user(session, user.id)

    await crud.save_message(
        session,
        conversation_id=conversation.id,
        direction="in",
        content=incoming_text,
        msg_type="text",
        ig_message_id=ig_message_id,
    )

    history = await crud.get_recent_messages(session, conversation.id, limit=settings.MAX_HISTORY_MESSAGES)
    memories = await get_relevant_memories(session, user.id)

    messages = build_messages(username, memories, history[:-1], incoming_text)

    try:
        response = await llm_router.generate(messages)
        reply_text = response.text
        await crud.log_llm_usage(session, response.provider, response.tokens_used, success=True)
    except LLMProviderError as exc:
        log.error("LLM generation failed for user %s: %s", ig_scoped_id, exc)
        await crud.log_llm_usage(session, "none", None, success=False, error=str(exc))
        reply_text = FALLBACK_REPLY
        response = None

    await crud.save_message(
        session,
        conversation_id=conversation.id,
        direction="out",
        content=reply_text,
        msg_type="text",
        model_used=response.model if response else None,
        tokens_used=response.tokens_used if response else None,
    )

    return reply_text
