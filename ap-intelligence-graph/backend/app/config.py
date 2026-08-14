"""Environment/config loading.

Central place that decides, once, whether we have a live OpenAI key. Every
other module asks `settings.has_openai_key` rather than touching os.environ
directly, so swapping providers is a one-line change (see app/llm/factory.py).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}"
    )
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
