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

    # --- AI provider selection ---
    # ai_provider: which backend drives the router + generator LLMs
    #   options: openai | claude | gemini | github_copilot
    ai_provider: str = "openai"
    # embedding_provider: which backend drives RAG embeddings
    #   options: openai | gemini
    embedding_provider: str = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    router_model: str = "gpt-4.1-mini"
    generator_model: str = "gpt-4.1"
    embedding_model: str = "text-embedding-3-small"

    # Anthropic / Claude
    anthropic_api_key: str = ""

    # Google Gemini
    gemini_api_key: str = ""

    # GitHub Copilot (OpenAI-compatible chat completions)
    github_copilot_token: str = ""
    github_copilot_base_url: str = "https://api.githubcopilot.com"

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_schema: str = "public"

    knowledge_top_k: int = 8
    final_context_k: int = 4
    line_max_message_chars: int = 4500
    router_confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    skills_dir: str = "skills"

    # P2 multi-seed retrieval（spec-14 / task-14）
    fusion_strategy: str = "max"   # max | mean | rrf
    max_seeds: int = 5

    # P3 sufficiency（spec-15 / task-15）
    sufficiency_min_chunks: int = 2
    sufficiency_min_top_score: float = 0.4
    sufficiency_min_feature_overlap: int = 1

    # P4 judge + reflection（spec-17 / task-17）
    judge_enabled: bool = True
    judge_model: str = ""              # 空字串 → 沿用 router_model
    judge_min_axis: int = 6            # 各軸最低分
    judge_min_mean: float = 7.0        # 平均最低分
    max_reflection_retries: int = 1    # 硬上限 2

    # 三變體並陳（spec-19 / task-19）
    graph_variant: str = "reflection"  # basic | selfrag | reflection

    # Observability（spec-22 / task-22）
    observability_enabled: bool = True
    observability_persist: bool = False    # 寫 Supabase graph_traces
    trace_dir: str = ".traces"

    # Knowledge Store backend（spec-24 / task-24）
    knowledge_store_backend: str = "supabase"  # supabase | sqlite_vec | pinecone
    sqlite_vec_path: str = ".kb/local.db"
    sqlite_vec_dim: int = 1536                  # OpenAI text-embedding-3-small
    pinecone_api_key: str = ""
    pinecone_index: str = "rag-lessons"

    # HITL + Persistence（spec-21 / task-21）
    hitl_enabled: bool = False
    hitl_always_review_skills: list[str] = []
    checkpoint_backend: str = "memory"   # memory | sqlite | none
    checkpoint_sqlite_path: str = ".checkpoints/rag.db"

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
