from __future__ import annotations

from fastapi import FastAPI

from app.line.webhook import router as line_router


def create_app() -> FastAPI:
    app = FastAPI(title="project-linebot-rag-skills")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(line_router)
    return app


app = create_app()
