"""tcm_corpus/02 — 醫砭線上典藏 /db/ 資料庫接入 pipeline。

/db/ 路徑與 01 的 /shu/ 不同 — 它是「分類型資料庫」：
    did = database id（例如 syp = 神農本草經）
    cat = 分類維度（lei = 類別、bop = 注音、shu = 卷別 ...）
    URL 樣式：/db/?did=<dbid>&cat=<axis>

實務上常見組合：
    /db/?did=syp&cat=lei  → 神農本草經 / 按類別瀏覽
    /db/?did=syp&cat=bop  → 神農本草經 / 按注音瀏覽
    /db/?did=hzm&cat=lei  → 黃帝內經 / 按類別

與 01 共享同一個站點 + yb-* CSS 框架，但 source code 拆開讓 worker
依不同 extractor_schema 處理。

授權須知：與 01 相同，本檔不重複；請先讀 01_seed_yibian_shu.py 與
https://yibian.hopto.org/declare/?de=co。

執行方式：
    python examples/tcm_corpus/02_seed_yibian_db.py
    python examples/tcm_corpus/02_seed_yibian_db.py --did syp
    python examples/tcm_corpus/02_seed_yibian_db.py --did hzm --cat bop
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.crawl_queue import insert_new_pending_jobs
from utils.db_types import (
    ArticleExtractorSchema,
    CrawlPageType,
    CrawlQueueInsert,
    CrawlQueuePayload,
    ExtractorSchema,
    FieldMapping,
    ListExtractorSchema,
    SourceConfig,
    SourceInsert,
    to_insert_dict,
)
from utils.supabase_client import get_crawler_table

PROJECT_ID = os.getenv("PROJECT_ID", "demo-project")
DEFAULT_DID = "syp"   # 神農本草經
DEFAULT_CAT = "lei"   # 類別軸
SITE_BASE = "https://yibian.hopto.org"


YIBIAN_DB_SOURCE = SourceInsert(
    project_id=PROJECT_ID,
    code="yibian-db",
    name="醫砭 中醫資料庫 (db)",
    description=(
        "醫砭線上中醫典藏的 /db/ 路徑（藥典 / 病典 / 證典等分類資料庫）。"
        "與 yibian-shu 共享同一站點，但分類軸不同（lei / bop / shu）。"
        "授權：所有權利保留，請見 https://yibian.hopto.org/declare/?de=co"
    ),
    base_url=SITE_BASE,
    domain="yibian.hopto.org",
    crawler_url=f"{SITE_BASE}/db/?did={DEFAULT_DID}&cat={DEFAULT_CAT}",
    config=SourceConfig(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36 "
            "(educational ch10/tcm_corpus; please email site admin if scraping seriously)"
        ),
        # /db/ 同樣有 AJAX 載入內容
        wait_until="networkidle",
        timeout_ms=30_000,
        block_resources=["image", "font", "media", "stylesheet"],
    ),
    extractor_schema=ExtractorSchema(
        list=ListExtractorSchema(
            # /db/ 的條目連結 pattern 為 ?did=XX&cat=XX&sn=XX 或類似
            item_selector="a[href*='did=']",
            link_selector="a[href*='did=']",
            title_selector="a[href*='did=']",
        ),
        article=ArticleExtractorSchema(
            title_selector="h1, h2, .yb-db-title",
            content_selector=(
                "article, main, [role='main'], "
                ".yb-db-content, .yb-pad-s > div.yb-row"
            ),
            remove_selectors=[
                ".yb-most-top-div",
                "#yb-topnav",
                ".yb-bar-item",
                "#we-use-cookie",
                "script",
                "style",
                ".yb-apng",
            ],
        ),
    ),
    field_mapping=FieldMapping(
        title="title",
        content_text="content_text",
    ),
    is_enabled=True,
    schedule_cron=None,
    created_by="seed-script:tcm_corpus",
)


def build_seed_url(did: str, cat: str) -> dict:
    return {
        "url": f"{SITE_BASE}/db/?did={did}&cat={cat}&js=0",
        "page_type": CrawlPageType.LIST,
        "priority": 200,
        "payload": CrawlQueuePayload(
            discovered_from="seed",
            depth=0,
            meta={"did": did, "cat": cat},
        ),
    }


def seed_source() -> dict:
    payload = to_insert_dict(YIBIAN_DB_SOURCE)
    result = (
        get_crawler_table("sources")
        .upsert(payload, on_conflict="project_id,code")
        .execute()
    )
    return result.data[0]


def enqueue_seed(source_id: str, did: str, cat: str) -> tuple[int, int]:
    seed = build_seed_url(did, cat)
    payload = to_insert_dict(
        CrawlQueueInsert(
            project_id=PROJECT_ID,
            source_id=source_id,
            url=seed["url"],
            page_type=seed["page_type"],
            priority=seed["priority"],
            payload=seed["payload"],
        )
    )
    return insert_new_pending_jobs(source_id, [payload])


def main() -> None:
    parser = argparse.ArgumentParser(description="醫砭 /db/ → ch08 pipeline")
    parser.add_argument("--did", default=DEFAULT_DID,
                        help=f"資料庫 id（預設 {DEFAULT_DID}：神農本草經）")
    parser.add_argument("--cat", default=DEFAULT_CAT,
                        help=f"分類軸（lei / bop / shu，預設 {DEFAULT_CAT}）")
    args = parser.parse_args()

    print("=" * 60)
    print("tcm_corpus/02 — 醫砭 /db/ 接入 crawler pipeline")
    print("=" * 60)
    print(f"  project_id : {PROJECT_ID}")
    print(f"  code       : {YIBIAN_DB_SOURCE.code}")
    print(f"  did        : {args.did}")
    print(f"  cat        : {args.cat}")
    print(f"  seed URL   : {SITE_BASE}/db/?did={args.did}&cat={args.cat}&js=0")
    print()
    print("⚠️  授權提醒：本站採「著作權所有」，非開放授權。")
    print("    https://yibian.hopto.org/declare/?de=co")
    print()

    source = seed_source()
    print(f"[OK] source 已 upsert：{source['id']}")

    enqueued, skipped = enqueue_seed(source["id"], args.did, args.cat)
    print(f"[OK] crawl_queue：新增 {enqueued} 筆，已存在略過 {skipped} 筆")
    print()
    print("─" * 60)
    print("下一步：")
    print("  python -m utils.worker.main")
    print("  python ch09-rag-bridge/04_end_to_end_demo.py")


if __name__ == "__main__":
    main()
