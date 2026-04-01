"""
Ch08-01 — 驗證 Supabase 連線與 crawler schema 存取。

執行前確認：
    1. .env 已設定 SUPABASE_URL / SUPABASE_SERVICE_KEY / PROJECT_ID
    2. Supabase Dashboard → Settings → API → Extra schemas 已加入 crawler
    3. 001_extensions.sql + 003_crawler_schema.sql 已執行

執行方式：
    python ch08-supabase/01_connect_supabase.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import get_crawler_table, get_supabase


def check_connection() -> bool:
    """驗證 Supabase 連線是否正常。"""
    try:
        supabase = get_supabase()
        # 用最輕量的查詢確認連線：select 1 筆 sources（即使空表也不會報錯）
        get_crawler_table("sources").select("id").limit(1).execute()
        print("[✓] Supabase 連線成功")
        return True
    except EnvironmentError as e:
        print(f"[✗] 環境設定錯誤：{e}")
        return False
    except Exception as e:
        print(f"[✗] 連線失敗：{e}")
        print("    請確認：")
        print("    1. .env 的 SUPABASE_URL / SUPABASE_SERVICE_KEY 是否正確")
        print("    2. Supabase Dashboard → Settings → API → Extra schemas 是否已加入 crawler")
        return False


def check_schema_tables() -> bool:
    """確認 crawler schema 的核心資料表皆可存取。"""
    tables = [
        "sources",
        "crawl_runs",
        "crawl_queue",
        "source_pages",
        "articles",
    ]
    all_ok = True
    print("\n[資料表存取檢查]")
    for table in tables:
        try:
            result = get_crawler_table(table).select("id").limit(1).execute()
            count_result = get_crawler_table(table).select("*", count="exact").execute()
            count = count_result.count if count_result.count is not None else "?"
            print(f"  [✓] crawler.{table:<25} （現有 {count} 筆）")
        except Exception as e:
            print(f"  [✗] crawler.{table:<25} 存取失敗：{e}")
            all_ok = False
    return all_ok


def list_sources() -> None:
    """列出現有的爬蟲來源設定。"""
    result = get_crawler_table("sources").select(
        "id, code, name, is_enabled, last_run_at"
    ).order("created_at").execute()

    sources = result.data or []
    print(f"\n[Sources 清單] 共 {len(sources)} 筆")

    if not sources:
        print("  （尚無資料，請執行 02_seed_source.py 建立來源設定）")
        return

    print(f"  {'code':<20} {'name':<25} {'enabled':<10} last_run_at")
    print("  " + "-" * 70)
    for s in sources:
        enabled = "✓" if s["is_enabled"] else "✗"
        last_run = s["last_run_at"] or "—"
        print(f"  {s['code']:<20} {s['name']:<25} {enabled:<10} {last_run}")


def check_rpc() -> bool:
    """確認 lease_next_crawl_job RPC 可呼叫。

    注意：此 RPC 定義在 crawler schema，需確認 Supabase 已將 crawler
    列入 exposed schemas，否則此呼叫會失敗。
    """
    print("\n[RPC 可用性檢查]")
    try:
        # 用不存在的 worker_id 呼叫，空佇列時回傳空陣列（正常）
        result = get_supabase().schema("crawler").rpc(
            "lease_next_crawl_job",
            {"p_worker_id": "probe-worker"},
        ).execute()
        print("  [✓] lease_next_crawl_job() 可呼叫")
        if not result.data:
            print("  [i] 佇列目前為空（執行 03_enqueue_urls.py 加入任務）")
        return True
    except Exception as e:
        print(f"  [✗] RPC 呼叫失敗：{e}")
        print("  請確認 crawler schema 已在 Supabase → Settings → API → Extra schemas 中")
        return False


def main() -> bool:
    print("=" * 50)
    print("Ch08 — Supabase 連線驗證")
    print("=" * 50)

    if not check_connection():
        return False

    if not check_schema_tables():
        return False

    list_sources()
    check_rpc()

    print("\n🎉 環境就緒，可以開始 ch08 整合！")
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
