"""ch09 Step 4 — 端對端驗收：確認爬蟲資料已可被 RAG Bot 使用。

本腳本只負責 project-playwright 端的驗收：
  1. 確認 crawler.articles 有資料
  2. 確認 category / source_type 欄位已填寫
  3. 印出後續在 project-linebot-rag-skills 執行的指令

完整端對端流程：
  ┌─────────────────────────────────────────────┐
  │  [project-playwright]                        │
  │  python utils/worker/main.py                 │
  │      → crawler.articles ← (Supabase)         │
  └────────────────┬────────────────────────────┘
                   │ 共用 Supabase 實例
  ┌────────────────▼────────────────────────────┐
  │  [project-linebot-rag-skills]                │
  │  python scripts/ingest.py articles           │
  │      → embed → private_knowledge             │
  │  → LINE Bot 即可回答爬下來的內容              │
  └─────────────────────────────────────────────┘

執行：
    python ch09-rag-bridge/end_to_end_demo.py [--category <cat>]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

from utils.config import RAG_VERIFY_QUERY_LIMIT
from utils.supabase_client import get_async_supabase


async def check_articles(category: str | None) -> dict:
    client = await get_async_supabase()

    q = (
        client.schema("crawler")
        .table("articles")
        .select("source_url, category, source_type, content_hash, content_text")
    )
    if category:
        q = q.eq("category", category)

    result = await q.limit(RAG_VERIFY_QUERY_LIMIT).execute()
    rows = result.data or []

    total = len(rows)
    has_content = sum(1 for r in rows if r.get("content_text"))
    has_category = sum(1 for r in rows if r.get("category"))
    has_source_type = sum(1 for r in rows if r.get("source_type") == "web")

    return {
        "total": total,
        "has_content": has_content,
        "has_category": has_category,
        "has_source_type": has_source_type,
        "sample_urls": [r["source_url"] for r in rows[:3]],
    }


def print_report(stats: dict, category: str | None) -> None:
    cat_filter = f" (category={category!r})" if category else ""
    print(f"\n{'='*60}")
    print(f"  crawler.articles 驗收報告{cat_filter}")
    print(f"{'='*60}")
    print(f"  總文章數       : {stats['total']}")
    print(f"  有 content_text: {stats['has_content']}")
    print(f"  有 category    : {stats['has_category']}")
    print(f"  source_type=web: {stats['has_source_type']}")

    if stats["sample_urls"]:
        print(f"\n  樣本 URL：")
        for u in stats["sample_urls"]:
            print(f"    {u[:70]}")

    ok = stats["total"] > 0 and stats["has_content"] > 0
    print(f"\n  狀態: {'✅ 可以進行 embed' if ok else '❌ 資料不足，請先執行爬蟲'}")

    if ok:
        cat_arg = f"--category {category}" if category else "--category <your-category>"
        print(f"\n{'─'*60}")
        print("  下一步（在 project-linebot-rag-skills/ 執行）：")
        print(f"\n    python scripts/ingest.py articles {cat_arg}")
        print(f"\n  完成後可對 LINE Bot 提問，驗證知識庫已更新。")
    print(f"{'='*60}\n")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default=None, help="只驗收指定分類")
    args = parser.parse_args()

    print("⏳  查詢 crawler.articles ...")
    stats = await check_articles(args.category)
    print_report(stats, args.category)


if __name__ == "__main__":
    asyncio.run(main())
