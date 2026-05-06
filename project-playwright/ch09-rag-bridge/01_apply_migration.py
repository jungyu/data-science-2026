"""ch09 Step 1 — 驗證 Migration 是否已套用。

本腳本連接 Supabase，確認 crawler.articles 是否已存在
  - category    欄位
  - source_type 欄位

若尚未套用，印出完整 SQL 並提示操作指令。

執行：
    python ch09-rag-bridge/01_apply_migration.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

MIGRATION_FILE = PROJECT_ROOT / "supabase" / "migrations" / "20260507000000_articles_rag_columns.sql"

REQUIRED_COLUMNS = ["category", "source_type"]


async def check_columns(client) -> dict[str, bool]:
    """逐一嘗試 SELECT 欄位，判斷是否存在。

    information_schema 在大多數 Supabase 部署中無法透過 PostgREST 存取，
    改用「SELECT <col> LIMIT 0」：成功 → 存在，PostgREST 回 400/PGRST204 → 不存在。
    """
    status: dict[str, bool] = {}
    for col in REQUIRED_COLUMNS:
        try:
            await (
                client.schema("crawler")
                .table("articles")
                .select(col)
                .limit(0)
                .execute()
            )
            status[col] = True
        except Exception:
            status[col] = False
    return status


def print_migration_sql() -> None:
    if MIGRATION_FILE.exists():
        print("\n" + "─" * 60)
        print("  Migration SQL（可直接貼入 Supabase Dashboard → SQL Editor）：")
        print("─" * 60)
        print(MIGRATION_FILE.read_text(encoding="utf-8"))
        print("─" * 60)
    else:
        print(f"\n⚠️  找不到 migration 檔：{MIGRATION_FILE}")


async def main() -> None:
    from supabase import create_async_client

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("❌  請先設定 SUPABASE_URL 與 SUPABASE_SERVICE_KEY（.env 或環境變數）")
        sys.exit(1)

    print(f"⏳  連接 Supabase：{url}")
    client = await create_async_client(url, key)

    print("⏳  檢查 crawler.articles 欄位 ...")
    status = await check_columns(client)

    all_ok = all(status.values())
    print()
    print("─" * 50)
    print(f"  {'欄位':<20} {'狀態'}")
    print("─" * 50)
    for col, ok in status.items():
        icon = "✅" if ok else "❌  （缺少）"
        print(f"  {col:<20} {icon}")
    print("─" * 50)

    if all_ok:
        print("\n✅  Migration 已套用，可繼續執行 02_verify_rag_schema.py")
    else:
        print("\n❌  欄位尚未建立，請套用 migration：")
        print()
        print("  方法 A — supabase CLI（推薦）：")
        print("    supabase db push")
        print()
        print("  方法 B — 手動貼 SQL：")
        print_migration_sql()
        print()
        print("  套用完成後重新執行本腳本確認。")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
