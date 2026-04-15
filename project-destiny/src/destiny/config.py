from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    openai_api_key: str
    embedding_model: str
    embedding_dim: int
    chat_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ["DATABASE_URL"],
            openai_api_key=os.environ["OPENAI_API_KEY"],
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_dim=int(os.getenv("EMBEDDING_DIM", "1536")),
            chat_model=os.getenv("CHAT_MODEL", "claude-sonnet-4-6"),
        )


settings = Settings.from_env() if os.getenv("DATABASE_URL") else None
