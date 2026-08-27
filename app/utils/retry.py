"""
app/utils/retry.py

A small async retry decorator with exponential backoff.
Used anywhere we call an external API that can fail transiently
(Instagram Graph API, Groq, Gemini).

Usage:
    @with_retry(max_attempts=3, base_delay=1.0)
    async def call_api():
        ...
"""

import asyncio
import functools
from typing import Callable, Tuple, Type

from app.utils.logging import get_logger

log = get_logger("RETRY")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001 - intentional broad catch here only
                    last_exc = exc
                    if attempt == max_attempts:
                        log.error("%s failed after %d attempts: %s", func.__name__, attempt, exc)
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    log.warning(
                        "%s attempt %d/%d failed (%s), retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, delay,
                    )
                    await asyncio.sleep(delay)
            raise last_exc  # pragma: no cover - unreachable safeguard

        return wrapper

    return decorator
