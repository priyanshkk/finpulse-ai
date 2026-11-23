"""Environment-driven configuration for FinPulse AI.

Every value here can be overridden without editing code. No secret has a
default value other than an empty string.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings resolved from environment variables."""

    database_url: str
    gemini_api_key: str
    gemini_model: str
    max_upload_mb: int
    seed_on_start: bool
    app_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the current process environment."""
        try:
            max_upload = int(os.getenv("MAX_UPLOAD_MB", "10"))
        except ValueError:
            max_upload = 10
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/finpulse.db"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            max_upload_mb=max_upload,
            seed_on_start=os.getenv("SEED_ON_START", "1") == "1",
            app_dir=Path(__file__).resolve().parent,
        )

    @property
    def ai_enabled(self) -> bool:
        """Whether the Gemini receipt parser can be used.

        Placeholder values from ``.env.example`` are treated as "not configured"
        so a fresh checkout stays offline and fast.
        """
        return bool(self.gemini_api_key) and self.gemini_api_key not in {"your_key_here", "changeme"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance for this process."""
    return Settings.from_env()
