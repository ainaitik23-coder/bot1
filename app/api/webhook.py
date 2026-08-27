"""
app/api/webhook.py

The only two endpoints Meta talks to:
  GET  /webhook  -- one-time verification handshake
  POST /webhook  -- actual incoming DM events

IMPORTANT: this file stays "thin" on purpose. The POST handler verifies
the signature, parses events, and immediately hands off to a background
task -- it does NOT wait for the LLM call before responding. Meta expects
a fast 200 OK; if you're slow, Meta will retry the same event, and if you
were doing LLM calls inline that means duplicate replies.
"""

import json

from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.config import settings
from app.database.database import get_session
from app.database import crud
from app.conversation.manager import handle_incoming_message
from app.instagram.messaging import reply_to_user
from app.instagram.webhook import parse_events, verify_signature
from app.utils.logging import get_logger

router = APIRouter()
log = get_logger("WEBHOOK")


@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Meta calls this once when you save the webhook config in the dashboard.
    Must echo back hub.challenge if hub.verify_token matches ours.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.IG_VERIFY_TOKEN:
        log.info("Webhook verified successfully by Meta")
        return Response(content=challenge, media_type="text/plain")

    log.warning("Webhook verification failed (mode=%s, token_match=%s)", mode, token == settings.IG_VERIFY_TOKEN)
    return Response(content="Verification failed", status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_signature(raw_body, signature):
        log.warning("Rejected webhook POST with invalid signature")
        return Response(status_code=403)

    payload = json.loads(raw_body)
    events = parse_events(payload)

    for event in events:
        # Enqueue processing -- respond to Meta immediately, don't block on the LLM call.
        background_tasks.add_task(_process_event, event)

    # Always 200 quickly, even if there were zero relevant events in this payload.
    return Response(status_code=200)


async def _process_event(event) -> None:
    """Runs in the background: dedupe check -> full conversation pipeline -> send reply."""
    async with get_session() as session:
        if event.ig_message_id and await crud.message_exists(session, event.ig_message_id):
            log.info("Duplicate event %s ignored (already processed)", event.ig_message_id)
            return

        reply_text = await handle_incoming_message(
            session=session,
            ig_scoped_id=event.sender_id,
            username=None,  # Instagram webhooks don't include username; fetched later if needed
            incoming_text=event.text,
            ig_message_id=event.ig_message_id,
        )

    await reply_to_user(event.sender_id, reply_text)
