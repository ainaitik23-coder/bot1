"""
app/ai/base.py

Common interface every LLM provider must follow. This is what makes the
router able to swap between Groq/Gemini/anything-else without caring
about their different APIs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tokens_used: int | None = None


class LLMProviderError(Exception):
    """Raised when a provider fails (bad key, rate limit, timeout, etc.)."""
    pass


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, messages: list[dict], api_key: str) -> LLMResponse:
        """
        messages: list of {"role": "system"|"user"|"assistant", "content": str}
        api_key: the specific key to use for this attempt (router handles rotation)
        Raises LLMProviderError on any failure so the router can move to the next key/provider.
        """
        raise NotImplementedError
