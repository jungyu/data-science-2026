"""Ch10-03 — 把 CBETA 經文接入 ch08 pipeline（SPA 案例）。

對照 examples/drone_data/01_seed_px4_docs.py：
    PX4 是「假 SPA」（Docusaurus 預渲染），domcontentloaded 就抓得到。
    CBETA 是「真 SPA」，初次 HTML 是空殼、內容由 JS 載入。

本腳本展示對「真 SPA」如何設定：
    config.wait_until = "load"        # 全頁載入完才放行
    extractor_schema   裡的 selector  # 用 multi-fallback 容忍 CBETA 多版型

對象經典：
    B0067_001 — 補編 第 67 號文獻 卷 1
    （CBETA 補編收錄罕見、歷代主流大藏經未收的佛教文獻）

授權須知：
    CBETA 釋出之文獻採「CBETA 自訂授權條款」，要點：
      1. 非營利、學術 / 個人研究目的可自由下載、複製
      2. 必須註明出處（CBETA、卷別、版本日期）
      3. 不得修改後重新發行
      4. 詳細條款：https://cbetaonline.dila.edu.tw/zh/copyright
    本腳本僅示範「個人 RAG 知識庫」的合理使用情境，請勿用於商業重新發行。

執行方式：
    python ch10-spa/03_cbeta_ingest.py
    python ch10-spa/03_cbeta_ingest.py --juans 1,2,3
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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

# 預設只爬 B0067 第 1 卷；可從 --juans 改為多卷
DEFAULT_TEXT_CODE = "B0067"
DEFAULT_JUANS = "1"


CBETA_SOURCE = SourceInsert(
    project_id=PROJECT_ID,
    code="cbeta-canon",
    name="CBETA 中華電子佛典",
    description=(
        "中華電子佛典協會（CBETA）線上閱讀典藏。"
        "SPA 架構，本來源僅作 ch10 SPA scraping 教學示範。"
        "授權：https://cbetaonline.dila.edu.tw/zh/copyright"
    ),
    base_url="https://cbetaonline.dila.edu.tw",
    domain="cbetaonline.dila.edu.tw",
    crawler_url="https://cbetaonline.dila.edu.tw/zh/B0067_001",
    config=SourceConfig(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36 "
            "(ch10-spa educational; contact via project README)"
        ),
        # SPA 用 "load" 比 "domcontentloaded" 穩 — 等到 window.onload 才放行；
        # extractor 內又會再 wait selector，雙保險
        wait_until="load",
        timeout_ms=30_000,
        # 經文閱讀器不需要圖片 / 字型 / 影片，加速並減少 CBETA 伺服器負擔
        block_resources=["image", "font", "media"],
    ),
    extractor_schema=ExtractorSchema(
        list=ListExtractorSchema(
            # B0067_001 本身是「文章頁」，不會有 list extractor 啟用；
            # 此欄留空 selector 作為 schema 完整性占位
            item_selector="nav.juan-nav a, .toc-list a",
            link_selector="a",
        ),
        article=ArticleExtractorSchema(
            # CBETA reader 多版型 — 標題可能在不同位置，用逗號 OR fallback
            title_selector="h1, .juan-title, .text-title, header h2",
            content_selector=(
                # SPA 渲染後的內文容器，依優先度多 selector OR
                "article.juan, .juan-content, .text-content, "
                "[role='main'] > div, #content"
            ),
            remove_selectors=[
                ".tool-bar",       # 上方工具列
                ".side-panel",     # 側邊欄
                ".annotation-popup",  # 註解彈窗
                ".footnote",       # 校注（避免污染正文，但若要校注可移除此行）
                "script",
                "style",
            ],
        ),
    ),
    field_mapping=FieldMapping(
        title="title",
        content_text="content_text",
    ),
    is_enabled=True,
    schedule_cron=None,  # CBETA 內容極少變動，不需要排程
    created_by="seed-script:ch10-spa",
)


def parse_juans(arg: str) -> list[int]:
    """支援 '1,2,3' 或 '1-5' 兩種寫法。"""
    arg = arg.strip()
    if "-" in arg:
        a, b = arg.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in arg.split(",") if x.strip()]


def build_seed_urls(text_code: str, juans: list[int]) -> list[dict]:
    """B0067_001、B0067_002... 的 URL pattern 推導。"""
    return [
        {
            "url": f"https://cbetaonline.dila.edu.tw/zh/{text_code}_{juan:03d}",
            "page_type": CrawlPageType.ARTICLE,  # 直接是文章頁
            "priority": 100,
            "payload": CrawlQueuePayload(
                discovered_from="seed",
                depth=0,
                meta={"text_code": text_code, "juan": juan},
            ),
        }
        for juan in juans
    ]


def seed_source() -> dict:
    payload = to_insert_dict(CBETA_SOURCE)
    result = (
        get_crawler_table("sources")
        .upsert(payload, on_conflict="project_id,code")
        .execute()
    )
    return result.data[0]


def enqueue_seeds(source_id: str, seeds: list[dict]) -> tuple[int, int]:
    payloads = [
        to_insert_dict(
            CrawlQueueInsert(
                project_id=PROJECT_ID,
                source_id=source_id,
                url=s["url"],
                page_type=s["page_type"],
                priority=s["priority"],
                payload=s["payload"],
            )
        )
        for s in seeds
    ]
    return insert_new_pending_jobs(source_id, payloads)


def main() -> None:
    parser = argparse.ArgumentParser(description="CBETA → ch08 pipeline ingest")
    parser.add_argument("--text-code", default=DEFAULT_TEXT_CODE,
                        help="經典代號（預設 B0067）")
    parser.add_argument("--juans", default=DEFAULT_JUANS,
                        help="卷別，支援 '1,2,3' 或 '1-5'（預設 1）")
    args = parser.parse_args()

    juans = parse_juans(args.juans)
    seeds = build_seed_urls(args.text_code, juans)

    print("=" * 60)
    print("Ch10-03 — CBETA 經文接入 crawler pipeline（SPA 教學案例）")
    print("=" * 60)
    print(f"  project_id : {PROJECT_ID}")
    print(f"  text_code  : {args.text_code}")
    print(f"  juans      : {juans}（共 {len(juans)} 卷）")
    print(f"  wait_until : load（SPA 友善策略）")
    print()
    print("⚠️  CBETA 授權提醒：個人 / 學術研究用途免費，須註明出處，")
    print("    禁止商業重新發行。詳見：")
    print("    https://cbetaonline.dila.edu.tw/zh/copyright")
    print()

    source = seed_source()
    print(f"[OK] source 已 upsert：{source['id']}")

    enqueued, skipped = enqueue_seeds(source["id"], seeds)
    print(f"[OK] crawl_queue：新增 {enqueued} 筆，已存在略過 {skipped} 筆")
    print()
    print("─" * 60)
    print("下一步：")
    print("  1. python -m utils.worker.main          # 啟動 async worker")
    print("  2. python ch09-rag-bridge/04_end_to_end_demo.py")
    print()
    print("💡 若 worker 顯示「extracted 0 chars」：")
    print("   表示 CBETA 的 DOM 結構與本腳本 selector 不符（網站改版）。")
    print("   解法：開 DevTools 找到實際內文容器，更新 extractor_schema 後")
    print("        重跑本腳本（upsert 會更新 source 設定）。")


if __name__ == "__main__":
    main()
