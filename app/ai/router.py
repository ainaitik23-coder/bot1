"""
app/ai/router.py

Tries Gemini keys first (left to right), then Groq keys, exactly matching
the order documented in .env.example. If a key/provider fails (rate limit,
invalid key, timeout, bad response) it moves to the next one automatically.
Only raises if EVERY key from EVERY provider fails.
"""

from app.ai.base import LLMProvider, LLMProviderError, LLMResponse
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider
from app.config import settings
from app.utils.logging import get_logger

log = get_logger("LLM")


class LLMRouter:
    def __init__(self) -> None:
        self._gemini = GeminiProvider()
        self._groq = GroqProvider()

        # (provider_instance, api_key) pairs, in the exact fallback order.
        self._attempts: list[tuple[LLMProvider, str]] = [
            (self._gemini, key) for key in settings.gemini_keys
        ] + [
            (self._groq, key) for key in settings.groq_keys
        ]

        if not self._attempts:
            log.warning("No LLM API keys configured! Check GEMINI_API_KEYS / GROQ_API_KEYS in .env")

    async def generate(self, messages: list[dict]) -> LLMResponse:
        last_error: Exception | None = None

        for provider, key in self._attempts:
            masked = key[:6] + "..." if len(key) > 6 else "***"
            try:
                response = await provider.generate(messages, key)
                log.info("Success via %s (key %s)", provider.name, masked)
                return response
            except LLMProviderError as exc:
                log.warning("%s (key %s) failed: %s -- trying next", provider.name, masked, exc)
                last_error = exc
                continue

        log.error("ALL %d keys exhausted across Gemini + Groq", len(self._attempts))
        raise LLMProviderError(f"All LLM providers/keys exhausted. Last error: {last_error}")


# Single shared instance for the whole app.
llm_router = LLMRouter()
