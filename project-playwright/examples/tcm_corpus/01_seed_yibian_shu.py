"""tcm_corpus/01 — 醫砭線上典藏 /shu/ 書籍接入 pipeline。

醫砭（https://yibian.hopto.org/）為沈藥子主持的中醫古籍 / 現代著作典藏。
本腳本對應 /shu/ 路徑：每本書一個 sno，目錄頁 cat=dir，章節用 cat=<chapter_id>。

目錄頁初次 HTML 不含真實 TOC（透過 jQuery AJAX 載入），需用 Playwright
等待 DOM 變動後才能擷取章節連結。

授權須知（重要）：
    yibian.hopto.org 頁尾：「著作權所有 ©2008～2026 智橐、醫砭、沈藥子」
    這是 "All rights reserved"，沒有明確的開放授權條款。
    本腳本僅作 ch10-spa 同類「動態載入 + 中文古籍」教學示範，
    請遵守：
      1. 個人 / 課堂研究：建議事先寫信告知站方
      2. 不要大量抓取：本站為個人 / 小團隊維運（hopto.org 動態 DNS）
         block_resources / rate limit 都要保守
      3. 商業用途：必須先取得書面授權
      4. 服務條款：https://yibian.hopto.org/declare/?de=po
      5. 著作權聲明：https://yibian.hopto.org/declare/?de=co

執行方式：
    python examples/tcm_corpus/01_seed_yibian_shu.py
    python examples/tcm_corpus/01_seed_yibian_shu.py --sno 43

下一步：
    python -m utils.worker.main
    python ch09-rag-bridge/04_end_to_end_demo.py
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
DEFAULT_SNO = 43  # 中醫很科學
SITE_BASE = "https://yibian.hopto.org"


YIBIAN_SHU_SOURCE = SourceInsert(
    project_id=PROJECT_ID,
    code="yibian-shu",
    name="醫砭 中醫典籍 (shu)",
    description=(
        "醫砭線上中醫典藏的 /shu/ 路徑（每本書一個 sno）。"
        "教學示範動態載入 (jQuery AJAX) 的書目站點，與 ch10 CBETA 互補。"
        "授權：所有權利保留，請見 https://yibian.hopto.org/declare/?de=co"
    ),
    base_url=SITE_BASE,
    domain="yibian.hopto.org",
    crawler_url=f"{SITE_BASE}/shu/?sno={DEFAULT_SNO}&cat=dir",
    config=SourceConfig(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36 "
            "(educational ch10/tcm_corpus; please email site admin if scraping seriously)"
        ),
        # 本站初次 HTML 是空殼，章節 TOC 由 AJAX 載入 → 需要 networkidle
        wait_until="networkidle",
        timeout_ms=30_000,
        # 站方為小團隊維運（hopto.org），盡可能減少資源請求
        block_resources=["image", "font", "media", "stylesheet"],
    ),
    extractor_schema=ExtractorSchema(
        list=ListExtractorSchema(
            # 醫砭使用自家 yb-* CSS 框架；TOC 章節連結通常以 ?sno=NN&cat=XX 形式
            # 用「凡是含 sno= 的連結」作為候選，再以 cat=dir / cat=bop / 語系切換被排除
            item_selector="a[href*='sno=']",
            link_selector="a[href*='sno=']",
            title_selector="a[href*='sno=']",
        ),
        article=ArticleExtractorSchema(
            # 章節內文容器：本站常見 yb-row / yb-pad-* 巢狀；用 main / article 保底
            title_selector="h1, h2, .yb-shu-title",
            content_selector=(
                "article, main, [role='main'], "
                ".yb-shu-content, .yb-pad-s > div.yb-row"
            ),
            remove_selectors=[
                ".yb-most-top-div",   # 頂部 logo / 導覽
                "#yb-topnav",          # 主導覽列
                ".yb-bar-item",        # 切換按鈕
                "#we-use-cookie",      # cookie 提示
                "script",
                "style",
                ".yb-apng",            # 廣告位置
            ],
        ),
    ),
    field_mapping=FieldMapping(
        title="title",
        content_text="content_text",
    ),
    is_enabled=True,
    schedule_cron=None,  # 古籍內容變動極少，無需排程
    created_by="seed-script:tcm_corpus",
)


def build_seed_url(sno: int) -> dict:
    """每本書的 TOC（目錄頁）作為列表種子；發現的章節 URL 由 worker 自動排入。"""
    return {
        "url": f"{SITE_BASE}/shu/?sno={sno}&cat=dir&xpd=8&js=0",
        # 用 xpd=8 展開最多層 TOC，js=0 走非 JS 版以減少 AJAX 依賴
        "page_type": CrawlPageType.LIST,
        "priority": 200,
        "payload": CrawlQueuePayload(
            discovered_from="seed",
            depth=0,
            meta={"sno": sno, "shu": True},
        ),
    }


def seed_source() -> dict:
    payload = to_insert_dict(YIBIAN_SHU_SOURCE)
    result = (
        get_crawler_table("sources")
        .upsert(payload, on_conflict="project_id,code")
        .execute()
    )
    return result.data[0]


def enqueue_seed(source_id: str, sno: int) -> tuple[int, int]:
    seed = build_seed_url(sno)
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
    parser = argparse.ArgumentParser(description="醫砭 /shu/ → ch08 pipeline")
    parser.add_argument("--sno", type=int, default=DEFAULT_SNO,
                        help=f"書籍編號（預設 {DEFAULT_SNO}：中醫很科學）")
    args = parser.parse_args()

    print("=" * 60)
    print("tcm_corpus/01 — 醫砭 /shu/ 接入 crawler pipeline")
    print("=" * 60)
    print(f"  project_id : {PROJECT_ID}")
    print(f"  code       : {YIBIAN_SHU_SOURCE.code}")
    print(f"  sno        : {args.sno}")
    print(f"  seed URL   : {SITE_BASE}/shu/?sno={args.sno}&cat=dir&xpd=8&js=0")
    print()
    print("⚠️  授權提醒：本站採「著作權所有」，非開放授權。")
    print("    個人 / 教學使用建議事先告知站方；商業用途必須取得授權。")
    print("    https://yibian.hopto.org/declare/?de=co")
    print()

    source = seed_source()
    print(f"[OK] source 已 upsert：{source['id']}")

    enqueued, skipped = enqueue_seed(source["id"], args.sno)
    print(f"[OK] crawl_queue：新增 {enqueued} 筆，已存在略過 {skipped} 筆")
    print()
    print("─" * 60)
    print("下一步：")
    print("  python -m utils.worker.main          # 啟動 async worker")
    print("  python ch09-rag-bridge/04_end_to_end_demo.py")


if __name__ == "__main__":
    main()
