"""
完整範例：新聞網站資料擷取。

綜合運用前面章節的技巧：
- BrowserManager 統一管理（utils/）
- Stealth 模式（ch06）
- 資料擷取與結構化（ch05）
- 匯出 JSON（ch05）
- 彈窗處理（ch06）

目標：擷取 Hacker News 首頁的文章列表。

執行方式：
    python examples/news_scraper.py
"""

import json
import sys
import time
from pathlib import Path

# 將專案根目錄加入 path 以便 import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.browser import BrowserManager
from utils.logger import setup_logger

OUTPUT_DIR = Path(__file__).parent.parent / "output"
logger = setup_logger("news_scraper")


def scrape_hacker_news(page) -> list[dict]:
    """擷取 Hacker News 首頁文章。"""
    page.goto("https://news.ycombinator.com/")
    page.wait_for_load_state("domcontentloaded")
    logger.info(f"已載入: {page.title()}")

    articles = []
    rows = page.locator("tr.athing")

    for i in range(rows.count()):
        row = rows.nth(i)
        rank_el = row.locator("span.rank")
        title_el = row.locator("td.title span.titleline > a")

        if title_el.count() == 0:
            continue

        rank = rank_el.text_content().strip().rstrip(".") if rank_el.count() > 0 else ""
        title = title_el.first.text_content().strip()
        url = title_el.first.get_attribute("href") or ""

        # 子行包含分數、作者、時間等資訊
        subtext_row = page.locator(f"#score_{row.get_attribute('id')}")
        score = ""
        if subtext_row.count() > 0:
            score = subtext_row.text_content().strip()

        articles.append({
            "rank": rank,
            "title": title,
            "url": url,
            "score": score,
        })

    return articles


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("啟動瀏覽器...")
    with BrowserManager(headless=True, stealth=True) as bm:
        page = bm.new_page()

        # 擷取資料
        start_time = time.time()
        articles = scrape_hacker_news(page)
        elapsed = time.time() - start_time

        logger.info(f"擷取完成：{len(articles)} 篇文章（耗時 {elapsed:.1f}s）")

        # 顯示前 10 篇
        print(f"\n{'排名':>4}  {'分數':>8}  標題")
        print("-" * 70)
        for article in articles[:10]:
            print(f"{article['rank']:>4}  {article['score']:>8}  {article['title'][:50]}")

        # 匯出 JSON
        output_path = OUTPUT_DIR / "hacker_news.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        logger.info(f"已匯出至 {output_path}")

        # 匯出統計
        urls_with_domain = [a for a in articles if a["url"].startswith("http")]
        domains = {}
        for article in urls_with_domain:
            from urllib.parse import urlparse
            domain = urlparse(article["url"]).netloc
            domains[domain] = domains.get(domain, 0) + 1

        top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n文章來源 Top 5：")
        for domain, count in top_domains:
            print(f"  {domain}: {count} 篇")


if __name__ == "__main__":
    main()
