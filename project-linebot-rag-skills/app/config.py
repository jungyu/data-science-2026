from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "project-linebot-rag-skills"

    line_channel_secret: str = ""
    line_channel_access_token: str = ""
    line_api_base: str = "https://api.line.me"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    router_model: str = "gpt-4.1-mini"
    generator_model: str = "gpt-4.1"
    embedding_model: str = "text-embedding-3-small"

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_schema: str = "public"

    knowledge_top_k: int = 8
    final_context_k: int = 4
    line_max_message_chars: int = 4500
    router_confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    skills_dir: str = "skills"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def skills_path(self) -> Path:
        path = Path(self.skills_dir)
        return path if path.is_absolute() else self.project_root / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
