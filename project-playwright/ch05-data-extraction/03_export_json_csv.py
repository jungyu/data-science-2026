"""
Ch05-03 — 匯出為 JSON 和 CSV。

將爬取的資料儲存為常用格式，
方便後續用 pandas、Excel 或其他工具分析。

執行方式：
    python ch05-data-extraction/03_export_json_csv.py
"""

import csv
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def scrape_links(page) -> list[dict]:
    """擷取頁面中所有連結的文字與 URL。"""
    links = page.locator("a[href]")
    data = []

    for i in range(links.count()):
        link = links.nth(i)
        text = (link.text_content() or "").strip()
        href = link.get_attribute("href") or ""

        if text and href and not href.startswith("#"):
            data.append({
                "text": text,
                "url": href,
                "is_external": href.startswith("http"),
            })

    return data


def export_json(data: list[dict], filepath: Path):
    """匯出為 JSON 格式。"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[JSON] 已匯出 {len(data)} 筆 → {filepath}")


def export_csv(data: list[dict], filepath: Path):
    """匯出為 CSV 格式。"""
    if not data:
        print("[CSV] 無資料可匯出")
        return

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"[CSV] 已匯出 {len(data)} 筆 → {filepath}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 擷取 Playwright 文件頁面的連結
        page.goto("https://playwright.dev/python/")
        page.wait_for_load_state("domcontentloaded")

        data = scrape_links(page)
        print(f"[擷取] 共取得 {len(data)} 個連結\n")

        # 預覽前 5 筆
        for item in data[:5]:
            icon = "🌐" if item["is_external"] else "📄"
            print(f"  {icon} [{item['text'][:30]}] → {item['url'][:50]}")

        # 匯出 JSON
        export_json(data, OUTPUT_DIR / "links.json")

        # 匯出 CSV
        export_csv(data, OUTPUT_DIR / "links.csv")

        # 匯出統計摘要
        summary = {
            "total_links": len(data),
            "external_links": sum(1 for d in data if d["is_external"]),
            "internal_links": sum(1 for d in data if not d["is_external"]),
            "source_url": page.url,
        }
        with open(OUTPUT_DIR / "links_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"[JSON] 已匯出摘要 → {OUTPUT_DIR / 'links_summary.json'}")

        browser.close()
        print(f"\n✅ 所有檔案已匯出至 {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
