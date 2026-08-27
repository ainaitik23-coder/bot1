"""
app/config.py

Loads all settings from .env into one typed object.
Import `settings` anywhere in the app instead of calling os.getenv() directly.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_keys(raw: str) -> List[str]:
    """Turns 'key1,key2, key3' into ['key1', 'key2', 'key3'], ignoring blanks."""
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Meta / Instagram
    IG_VERIFY_TOKEN: str
    IG_PAGE_ACCESS_TOKEN: str
    IG_APP_SECRET: str

    # LLM providers (raw comma-separated strings from .env)
    GEMINI_API_KEYS: str = ""
    GROQ_API_KEYS: str = ""

    # App
    DATABASE_URL: str = "sqlite+aiosqlite:///./memory/chat.db"
    LOG_LEVEL: str = "INFO"
    MAX_HISTORY_MESSAGES: int = 40

    @property
    def gemini_keys(self) -> List[str]:
        return _split_keys(self.GEMINI_API_KEYS)

    @property
    def groq_keys(self) -> List[str]:
        return _split_keys(self.GROQ_API_KEYS)


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is only parsed once."""
    return Settings()


settings = get_settings()
