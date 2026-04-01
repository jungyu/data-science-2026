"""
Ch08-02 — 在 crawler.sources 建立 Hacker News 來源設定。

sources 是整個 pipeline 的起點：
  - 定義要爬哪個站（base_url / crawler_url）
  - 儲存 Playwright 設定（config）
  - 定義如何擷取資料（extractor_schema）
  - 記錄上次執行時間（last_run_at）

只需執行一次；重複執行會 upsert（依 project_id + code 去重）。

執行方式：
    python ch08-supabase/02_seed_source.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_types import (
    ArticleExtractorSchema,
    ExtractorSchema,
    FieldMapping,
    ListExtractorSchema,
    SourceConfig,
    SourceInsert,
    to_insert_dict,
)
from utils.supabase_client import get_crawler_table

PROJECT_ID = os.getenv("PROJECT_ID", "demo-project")


# ── Hacker News 來源設定 ─────────────────────────────────────────

HN_SOURCE = SourceInsert(
    project_id=PROJECT_ID,
    code="hacker-news",
    name="Hacker News",
    description="Y Combinator 科技討論社群，每日精選科技文章與討論",
    base_url="https://news.ycombinator.com",
    domain="news.ycombinator.com",
    crawler_url="https://news.ycombinator.com/",
    config=SourceConfig(
        # 模擬真實瀏覽器的 User-Agent
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        wait_until="domcontentloaded",
        timeout_ms=15000,
        # 阻擋不必要的資源以加速爬取
        block_resources=["image", "font", "media", "stylesheet"],
    ),
    extractor_schema=ExtractorSchema(
        list=ListExtractorSchema(
            # HN 首頁每篇文章的列容器
            item_selector="tr.athing",
            # 每個 item 中的連結
            link_selector="td.title span.titleline > a",
            # 標題文字
            title_selector="td.title span.titleline > a",
        ),
        article=ArticleExtractorSchema(
            # HN 的文章通常是外部連結，title 從 <title> 取得
            title_selector="title",
            # 留空：HN 文章內容為外部頁面，此 schema 僅作示範
            content_selector=None,
        ),
    ),
    field_mapping=FieldMapping(
        title="title",
        author_name="author_name",
        published_at="published_at",
    ),
    is_enabled=True,
    schedule_cron="0 */6 * * *",  # 每 6 小時執行一次
    created_by="seed-script",
)


def seed_source() -> dict:
    """將 HN source 寫入 crawler.sources（upsert）。

    Returns:
        寫入後的 source 資料列（含 DB 自動產生的 id / created_at）
    """
    payload = to_insert_dict(HN_SOURCE)

    result = (
        get_crawler_table("sources")
        .upsert(payload, on_conflict="project_id,code")
        .execute()
    )

    return result.data[0]


def main():
    print("=" * 50)
    print("Ch08-02 — 建立 Hacker News 來源設定")
    print("=" * 50)
    print(f"  project_id : {PROJECT_ID}")
    print(f"  code       : {HN_SOURCE.code}")
    print(f"  crawler_url: {HN_SOURCE.crawler_url}")

    try:
        source = seed_source()
        print(f"\n[✓] 寫入成功")
        print(f"  source.id         : {source['id']}")
        print(f"  source.created_at : {source['created_at']}")
        print(f"  source.updated_at : {source['updated_at']}")
        print(f"\n  → 下一步：執行 03_enqueue_urls.py 加入種子 URL")
        return source
    except Exception as e:
        print(f"\n[✗] 寫入失敗：{e}")
        raise


if __name__ == "__main__":
    main()
