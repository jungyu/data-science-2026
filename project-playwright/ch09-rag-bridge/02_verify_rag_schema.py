"""ch09 Step 2 — 驗證 crawler.articles 與 KnowledgeChunkInsert 的欄位對應。

用途：在執行 IngestionPipeline 之前，先確認爬蟲已把資料寫進 DB，
並且格式能對應到 project-linebot-rag-skills 的 KnowledgeChunkInsert。

執行：
    python ch09-rag-bridge/02_verify_rag_schema.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# 讓 utils 可以 import
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()



async def main() -> None:
    from supabase import create_async_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]

    client = await create_async_client(url, key)

    result = (
        await client.schema("crawler")
        .table("articles")
        .select(
            "source_url, title, content_text, content_hash, "
            "category, source_type, meta, created_at"
        )
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )

    rows = result.data
    if not rows:
        print("⚠️  crawler.articles 目前沒有資料。")
        print("   請先執行 ch08-supabase/ 的爬蟲，或用 03_enqueue_urls.py 入列後跑 worker。")
        return

    print(f"✅  找到 {len(rows)} 筆文章（最新 3 筆）\n")

    print("─" * 60)
    print(f"{'crawler.articles 欄位':<28}  {'KnowledgeChunkInsert 欄位'}")
    print("─" * 60)
    mapping = [
        ("source_url",   "source_id / source_url"),
        ("title",        "title"),
        ("content_text", "content  (待 chunk)"),
        ("content_hash", "content_hash"),
        ("category",     "category"),
        ("source_type",  "source_type"),
        ("meta→tags",    "tags"),
        ("(EmbedBackend生成)", "embedding"),
    ]
    for src, dst in mapping:
        print(f"  {src:<26}→  {dst}")
    print("─" * 60)

    print("\n--- 樣本資料 ---")
    for i, row in enumerate(rows, 1):
        content_preview = (row.get("content_text") or "")[:80].replace("\n", " ")
        print(
            f"[{i}] {row.get('title', '(無標題)')[:50]}\n"
            f"     source_url  : {row.get('source_url', '')[:60]}\n"
            f"     content_hash: {row.get('content_hash', '(空)')}\n"
            f"     category    : {row.get('category') or '(空，pipeline 補 general)'}\n"
            f"     source_type : {row.get('source_type', 'web')}\n"
            f"     content 前80字: {content_preview!r}\n"
        )

    print("✅  Schema 驗證完畢。可執行 IngestionPipeline：")
    print("   cd ../project-linebot-rag-skills")
    print("   python scripts/ingest.py articles --category <category>")


if __name__ == "__main__":
    asyncio.run(main())
