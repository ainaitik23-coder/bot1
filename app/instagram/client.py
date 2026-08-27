"""
app/instagram/client.py

All direct calls to the Instagram Graph API live here. If Meta changes
an endpoint, this is the only file that needs to change.
"""

import httpx

from app.config import settings
from app.utils.logging import get_logger
from app.utils.retry import with_retry

log = get_logger("INSTAGRAM")

# graph.instagram.com is the current host for the Instagram API with Instagram Login.
GRAPH_URL = "https://graph.instagram.com/v21.0/me/messages"


class InstagramAPIError(Exception):
    pass


@with_retry(max_attempts=3, base_delay=1.5, exceptions=(httpx.RequestError, InstagramAPIError))
async def send_text_message(recipient_ig_scoped_id: str, text: str) -> dict:
    """Sends a plain text DM to a specific Instagram-scoped user id."""
    payload = {
        "recipient": {"id": recipient_ig_scoped_id},
        "message": {"text": text},
    }
    params = {"access_token": settings.IG_PAGE_ACCESS_TOKEN}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(GRAPH_URL, params=params, json=payload)

    if resp.status_code >= 400:
        log.error("Instagram send failed (%s): %s", resp.status_code, resp.text[:300])
        raise InstagramAPIError(f"Send failed: {resp.status_code} {resp.text[:200]}")

    log.info("Message sent to %s", recipient_ig_scoped_id)
    return resp.json()
