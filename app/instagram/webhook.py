"""
app/instagram/webhook.py

Two jobs:
1. Verify that an incoming webhook POST actually came from Meta
   (using X-Hub-Signature-256 + your app secret).
2. Parse the (fairly nested) webhook JSON payload into a simple,
   easy-to-use list of ParsedEvent objects.
"""

import hashlib
import hmac
from dataclasses import dataclass

from app.config import settings
from app.utils.logging import get_logger

log = get_logger("WEBHOOK")


@dataclass
class ParsedEvent:
    sender_id: str
    text: str
    ig_message_id: str | None


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Meta sends 'X-Hub-Signature-256: sha256=<hex digest>'.
    We recompute the HMAC using our app secret and compare.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = signature_header.removeprefix("sha256=")
    computed = hmac.new(
        key=settings.IG_APP_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, computed)


def parse_events(payload: dict) -> list[ParsedEvent]:
    """
    Instagram webhook payload shape (simplified):
    {
      "entry": [
        {
          "messaging": [
            {
              "sender": {"id": "..."},
              "message": {"mid": "...", "text": "..."}
            }
          ]
        }
      ]
    }
    We defensively .get() everything since Meta's payloads vary by event type
    (messages vs reactions vs read receipts, etc.) and we only care about text messages here.
    """
    events: list[ParsedEvent] = []

    for entry in payload.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            message = messaging_event.get("message")
            sender = messaging_event.get("sender", {})

            if not message or "text" not in message:
                # Not a text message (could be a reaction, read receipt, image, etc.)
                # Image/audio handling gets added in Phase 19-20.
                continue

            sender_id = sender.get("id")
            if not sender_id:
                log.warning("Skipping event with no sender id: %s", messaging_event)
                continue

            events.append(
                ParsedEvent(
                    sender_id=sender_id,
                    text=message["text"],
                    ig_message_id=message.get("mid"),
                )
            )

    return events
