from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.config import Settings, get_settings
from app.generator.responder import OpenAIGeneratorLLM, ResponseGenerator
from app.line.client import LineMessagingClient
from app.rag.embedder import OpenAICompatibleEmbedder
from app.rag.retriever import RAGRetriever
from app.router.intent_router import IntentRouter, OpenAIRouterLLM
from app.skills.registry import SkillRegistry
from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.logs_repo import LogsRepository
from app.storage.messages_repo import MessagesRepository
from app.storage.supabase_client import SupabaseRestClient


@dataclass(frozen=True)
class RuntimeServices:
    line_client: LineMessagingClient
    messages_repo: MessagesRepository
    skill_registry: SkillRegistry
    router: IntentRouter
    retriever: RAGRetriever
    responder: ResponseGenerator
    settings: Settings


@lru_cache(maxsize=1)
def get_supabase_client() -> SupabaseRestClient:
    return SupabaseRestClient(get_settings())


@lru_cache(maxsize=1)
def get_skill_registry() -> SkillRegistry:
    return SkillRegistry.from_directory(get_settings().skills_path)


@lru_cache(maxsize=1)
def get_line_client() -> LineMessagingClient:
    return LineMessagingClient(get_settings())


@lru_cache(maxsize=1)
def get_messages_repo() -> MessagesRepository:
    return MessagesRepository(get_supabase_client())


@lru_cache(maxsize=1)
def get_knowledge_repo() -> KnowledgeRepository:
    return KnowledgeRepository(get_supabase_client())


@lru_cache(maxsize=1)
def get_logs_repo() -> LogsRepository:
    return LogsRepository(get_supabase_client())


@lru_cache(maxsize=1)
def get_router() -> IntentRouter:
    settings = get_settings()
    llm = OpenAIRouterLLM(settings) if settings.openai_api_key else None
    return IntentRouter(llm=llm, confidence_threshold=settings.router_confidence_threshold)


@lru_cache(maxsize=1)
def get_retriever() -> RAGRetriever:
    settings = get_settings()
    return RAGRetriever(
        embedder=OpenAICompatibleEmbedder(settings),
        knowledge_repo=get_knowledge_repo(),
        logs_repo=get_logs_repo(),
        final_context_k=settings.final_context_k,
    )


@lru_cache(maxsize=1)
def get_responder() -> ResponseGenerator:
    settings = get_settings()
    llm = OpenAIGeneratorLLM(settings) if settings.openai_api_key else None
    return ResponseGenerator(llm=llm, line_max_message_chars=settings.line_max_message_chars)


def get_runtime_services() -> RuntimeServices:
    settings = get_settings()
    return RuntimeServices(
        line_client=get_line_client(),
        messages_repo=get_messages_repo(),
        skill_registry=get_skill_registry(),
        router=get_router(),
        retriever=get_retriever(),
        responder=get_responder(),
        settings=settings,
    )
