"""
Ch05-02 — 表格資料爬取與結構化。

示範如何從 HTML 表格中提取資料，
並轉換為 Python 字典列表（可直接轉成 DataFrame）。

執行方式：
    python ch05-data-extraction/02_table_scraping.py
"""

from playwright.sync_api import sync_playwright


def scrape_table(page, table_selector: str) -> list[dict]:
    """通用表格爬取函式：將 HTML 表格轉為字典列表。"""
    table = page.locator(table_selector)

    # 取得表頭
    headers = []
    th_elements = table.locator("thead th")
    for i in range(th_elements.count()):
        headers.append(th_elements.nth(i).text_content().strip())

    # 如果沒有 thead，用第一行 tr 當表頭
    if not headers:
        first_row = table.locator("tr").first
        cells = first_row.locator("th, td")
        headers = [cells.nth(i).text_content().strip() for i in range(cells.count())]

    # 取得表身資料
    rows = table.locator("tbody tr")
    data = []
    for i in range(rows.count()):
        cells = rows.nth(i).locator("td")
        row_data = {}
        for j in range(min(cells.count(), len(headers))):
            row_data[headers[j]] = cells.nth(j).text_content().strip()
        if row_data:
            data.append(row_data)

    return data


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 建立示範表格頁面
        page.set_content("""
        <html><body>
            <h1>台灣主要城市人口統計（示範資料）</h1>
            <table id="population" border="1" cellpadding="8">
                <thead>
                    <tr>
                        <th>城市</th>
                        <th>人口（萬）</th>
                        <th>面積（km²）</th>
                        <th>人口密度</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>台北市</td><td>251</td><td>271.8</td><td>9,230</td></tr>
                    <tr><td>新北市</td><td>403</td><td>2,052.6</td><td>1,964</td></tr>
                    <tr><td>桃園市</td><td>228</td><td>1,220.9</td><td>1,867</td></tr>
                    <tr><td>台中市</td><td>283</td><td>2,214.9</td><td>1,278</td></tr>
                    <tr><td>台南市</td><td>187</td><td>2,191.7</td><td>853</td></tr>
                    <tr><td>高雄市</td><td>276</td><td>2,951.9</td><td>935</td></tr>
                </tbody>
            </table>
        </body></html>
        """)

        # 使用通用函式爬取表格
        data = scrape_table(page, "#population")

        print(f"[表格] 爬取到 {len(data)} 筆資料\n")
        print(f"{'城市':<8} {'人口（萬）':>10} {'面積（km²）':>12} {'人口密度':>10}")
        print("-" * 48)
        for row in data:
            print(f"{row['城市']:<8} {row['人口（萬）']:>10} {row['面積（km²）']:>12} {row['人口密度']:>10}")

        # 如果有安裝 pandas，可直接轉成 DataFrame
        try:
            import pandas as pd
            df = pd.DataFrame(data)
            print(f"\n[Pandas] DataFrame shape: {df.shape}")
            print(df.to_string(index=False))
        except ImportError:
            print("\n[提示] 安裝 pandas 可將資料轉為 DataFrame：pip install pandas")

        browser.close()


if __name__ == "__main__":
    main()
