from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.rag.chunker import chunk_markdown
from app.rag.embedder import OpenAICompatibleEmbedder
from app.storage.supabase_client import SupabaseRestClient


async def ingest_path(path: Path, *, category: str) -> int:
    settings = get_settings()
    client = SupabaseRestClient(settings)
    embedder = OpenAICompatibleEmbedder(settings)
    text = path.read_text(encoding="utf-8")
    rows = []
    for index, chunk in enumerate(chunk_markdown(text), start=1):
        embedding = await embedder.embed_query(chunk)
        content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        rows.append(
            {
                "source_id": str(path),
                "source_type": "markdown",
                "title": f"{path.stem} #{index}",
                "content": chunk,
                "content_hash": content_hash,
                "category": category,
                "tags": [path.stem],
                "metadata": {"path": str(path), "chunk_index": index},
                "embedding": embedding,
            }
        )
    await client.upsert("private_knowledge", rows, on_conflict="content_hash")
    return len(rows)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--category", default="notes")
    args = parser.parse_args()

    total = 0
    for raw_path in args.paths:
        total += await ingest_path(Path(raw_path), category=args.category)
    print(f"Ingested {total} chunks.")


if __name__ == "__main__":
    asyncio.run(main())
