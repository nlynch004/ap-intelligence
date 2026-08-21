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
    admin_password: str | None = os.getenv("ADMIN_PASSWORD") or None

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
