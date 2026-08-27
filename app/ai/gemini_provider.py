"""
app/ai/gemini_provider.py

Calls Gemini's generateContent REST endpoint directly (no SDK dependency).

KEY-FORMAT NOTE (as of 2026):
Google AI Studio has migrated new keys from the old "AIzaSy..." format to
a new "AQ...." prefix format. Your AQ.-prefixed keys are valid Gemini API
keys -- they are NOT OAuth tokens. The catch: AQ. keys only work against
Gemini's *native* endpoint (what this file uses, via the x-goog-api-key
header below) -- they return 401 on the OpenAI-compatible endpoint
(/v1beta/openai/...) and on older SDK versions that haven't been updated
for the new format. If you ever see 401s with these keys, the fix is
almost always "use the native REST endpoint" (already done here), not
"generate a new key."
"""

import httpx

from app.ai.base import LLMProvider, LLMProviderError, LLMResponse

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _to_gemini_contents(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """
    Gemini separates the system prompt from the chat turns, and uses
    role 'model' instead of 'assistant'. Convert our common message
    format into Gemini's shape.
    """
    system_prompt = None
    contents = []
    for m in messages:
        if m["role"] == "system":
            system_prompt = m["content"]
            continue
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    return system_prompt, contents


class GeminiProvider(LLMProvider):
    name = "gemini"

    async def generate(self, messages: list[dict], api_key: str) -> LLMResponse:
        system_prompt, contents = _to_gemini_contents(messages)

        payload: dict = {"contents": contents, "generationConfig": {"temperature": 0.8, "maxOutputTokens": 512}}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(GEMINI_URL, headers=headers, json=payload)
        except httpx.RequestError as exc:
            raise LLMProviderError(f"Gemini network error: {exc}") from exc

        if resp.status_code == 429:
            raise LLMProviderError("Gemini rate limit hit")
        if resp.status_code in (400, 401, 403):
            raise LLMProviderError(f"Gemini key invalid/rejected ({resp.status_code}): {resp.text[:200]}")
        if resp.status_code >= 400:
            raise LLMProviderError(f"Gemini error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"Gemini unexpected response shape: {data}") from exc

        tokens = data.get("usageMetadata", {}).get("totalTokenCount")
        return LLMResponse(text=text, provider=self.name, model=GEMINI_MODEL, tokens_used=tokens)
