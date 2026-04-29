# AGENTS.md

## Project Goal

Build a private LINE Bot with lightweight RAG, Supabase pgvector, and skill-based intent routing.

## Stack

- Python 3.11+
- FastAPI
- Supabase
- pgvector
- LINE Messaging API
- OpenAI-compatible LLM provider
- pytest

## Architecture Rules

1. Router does not generate final answers.
2. Generator does not decide skill.
3. Retriever does not format final answers.
4. Skills are stored as markdown files and seeded into Supabase.
5. Every external LLM call must have a typed input and output schema.
6. Every RAG retrieval must be logged.
7. Webhook must return quickly; long processing goes to background task.

## Important Files

- `app/main.py`
- `app/line/webhook.py`
- `app/router/intent_router.py`
- `app/rag/retriever.py`
- `app/skills/loader.py`
- `app/generator/responder.py`
- `supabase/schema.sql`
- `supabase/functions.sql`
- `skills/*/SKILL.md`

## Testing Requirements

Implement tests for:

- router JSON parsing
- skill loading
- hybrid retrieval
- webhook signature validation
- response formatting

## Do Not

- Do not put secrets in code.
- Do not call LLM directly inside webhook handler.
- Do not hardcode skill prompts in Python if they belong in `SKILL.md`.
- Do not silently ignore failed retrieval.
- Do not introduce an MCP server for MVP unless another client must share this pipeline.
