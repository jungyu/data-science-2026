"""
Ch01-03 — 將網頁匯出為 PDF。

注意：PDF 匯出僅在 Chromium + headless 模式下可用。

執行方式：
    python ch01-first-steps/03_pdf_export.py
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # PDF 匯出必須使用 headless 模式
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com")

        # 匯出 PDF
        pdf_path = OUTPUT_DIR / "example_com.pdf"
        page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"},
            print_background=True,
        )
        print(f"[PDF] 匯出完成 → {pdf_path}")

        browser.close()


if __name__ == "__main__":
    main()
