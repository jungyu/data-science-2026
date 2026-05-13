"""
Ch05-03 — 匯出為 JSON 和 CSV。

將爬取的資料儲存為常用格式，
方便後續用 pandas、Excel 或其他工具分析。

執行方式：
    python ch05-data-extraction/03_export_json_csv.py
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import Page, sync_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "output"
LINK_FIELDS = ("text", "url", "is_external")


def scrape_links(page: Page) -> list[dict]:
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


def export_json(data: list[dict], filepath: Path) -> None:
    """匯出為 JSON 格式。"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[JSON] 已匯出 {len(data)} 筆 → {filepath}")


def export_csv(data: list[dict], filepath: Path) -> None:
    """匯出為 CSV 格式。

    使用 utf-8-sig（含 BOM）而非純 utf-8 — 這是給 Excel 開的 escape hatch：
    Excel 在 Windows 下若無 BOM 會以 Big5/ANSI 解讀 utf-8 CSV，導致中文亂碼。
    JSON 因下游皆為程式碼解析，固定用 utf-8（無 BOM）才符合慣例。
    """
    if not data:
        print("[CSV] 無資料可匯出")
        return

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LINK_FIELDS)
        writer.writeheader()
        writer.writerows(data)
    print(f"[CSV] 已匯出 {len(data)} 筆 → {filepath}")


def main() -> None:
    setup_stdout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 擷取 Playwright 文件頁面的連結
        page.goto("https://playwright.dev/python/")
        page.wait_for_load_state("domcontentloaded")

        data = scrape_links(page)
        print(f"[擷取] 共取得 {len(data)} 個連結")

        # 先匯出檔案，確保資料落地後再印預覽
        export_json(data, OUTPUT_DIR / "links.json")
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
        print(f"[JSON] 已匯出摘要 -> {OUTPUT_DIR / 'links_summary.json'}")

        browser.close()

    # 預覽前 5 筆（在瀏覽器關閉後印出，不影響匯出流程）
    print("\n[預覽] 前 5 筆連結：")
    for item in data[:5]:
        icon = "[EXT]" if item["is_external"] else "[INT]"
        print(f"  {icon} [{item['text'][:30]}] -> {item['url'][:50]}")

    print(f"\n[完成] 所有檔案已匯出至 {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
