"""
app/instagram/messaging.py

Thin wrapper around instagram/client.py -- kept as a separate file so
formatting/splitting logic (e.g. breaking a long reply into multiple DMs)
can live here later without touching the raw API client.
"""

from app.instagram.client import InstagramAPIError, send_text_message
from app.utils.logging import get_logger

log = get_logger("MESSAGING")

INSTAGRAM_MAX_MESSAGE_LENGTH = 1000  # Meta's documented text message limit


async def reply_to_user(recipient_ig_scoped_id: str, text: str) -> bool:
    """Returns True on success, False on failure (already logged)."""
    if len(text) > INSTAGRAM_MAX_MESSAGE_LENGTH:
        text = text[: INSTAGRAM_MAX_MESSAGE_LENGTH - 3] + "..."

    try:
        await send_text_message(recipient_ig_scoped_id, text)
        return True
    except InstagramAPIError as exc:
        log.error("Failed to deliver reply to %s: %s", recipient_ig_scoped_id, exc)
        return False
