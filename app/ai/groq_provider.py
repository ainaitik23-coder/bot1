"""
app/ai/groq_provider.py

Groq's API is OpenAI-compatible, so we just POST to their chat/completions
endpoint. Using raw httpx (not the groq SDK) keeps dependencies minimal and
gives us full control over error handling for the key-rotation router.
"""

import httpx

from app.ai.base import LLMProvider, LLMProviderError, LLMResponse

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Current, non-deprecated Groq model as of writing. Change here in ONE place
# if Groq deprecates it -- nowhere else in the codebase needs to know the model name.
GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(LLMProvider):
    name = "groq"

    async def generate(self, messages: list[dict], api_key: str) -> LLMResponse:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.8, "max_tokens": 512}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(GROQ_URL, headers=headers, json=payload)
        except httpx.RequestError as exc:
            raise LLMProviderError(f"Groq network error: {exc}") from exc

        if resp.status_code == 429:
            raise LLMProviderError("Groq rate limit hit")
        if resp.status_code == 401:
            raise LLMProviderError("Groq key invalid/expired")
        if resp.status_code >= 400:
            raise LLMProviderError(f"Groq error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"Groq unexpected response shape: {data}") from exc

        tokens = data.get("usage", {}).get("total_tokens")
        return LLMResponse(text=text, provider=self.name, model=GROQ_MODEL, tokens_used=tokens)
