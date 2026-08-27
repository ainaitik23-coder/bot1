"""
app/utils/logging.py

Gives every part of the app a logger that prefixes messages with a tag,
e.g. [WEBHOOK], [LLM], [DATABASE] -- makes grepping logs way easier.

Usage:
    from app.utils.logging import get_logger
    log = get_logger("WEBHOOK")
    log.info("Received event from user %s", user_id)
"""

import logging
import sys

from app.config import settings

_CONFIGURED = False


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%H:%M:%S")
    )
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(tag: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"[{tag}]")
