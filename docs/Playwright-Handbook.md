# 🧠 Head First Playwright 學習手冊
### 用真實瀏覽器，抓任何網站的資料！

> 📖 **參考來源**：[DataScout / playwright_base](https://github.com/jungyu/DataScout/tree/b81b6308c7aa63a953dcfdf30a7c40bce3a8e68e)

---

## 這本手冊適合誰？

✅ 用 `requests` 抓不到資料，因為頁面是 JavaScript 動態渲染的
✅ 被網站封鎖或偵測到是機器人
✅ 想模擬真人操作：點擊、輸入、滾動、翻頁
✅ 需要保存登入狀態、跨頁面保持 Session

---

# 第一章：Playwright 是什麼？跟 Selenium 有什麼不同？

---

## 🧩 先想一個問題

你開啟 Chrome，打開一個新聞網站，你「看到」的頁面和 `requests.get()` 拿到的 HTML **根本不一樣**！

```
你在瀏覽器看到的          requests 拿到的
─────────────────        ────────────────────
10 篇完整文章            <div id="app"></div>
清晰的分頁按鈕           <!-- JavaScript 還沒跑！ -->
動態載入的廣告
```

**Playwright 解決這個問題**：它控制一個真實的瀏覽器，讓 JavaScript 跑完，再讓你去抓資料。

---

## 📊 工具比較表

| 功能 | requests | Selenium | **Playwright** |
|------|----------|----------|----------------|
| 速度 | ⚡⚡⚡ 最快 | ⚡ 慢 | ⚡⚡ 快 |
| JS 渲染支援 | ❌ | ✅ | ✅ |
| 瀏覽器支援 | ❌ | Chrome/Firefox | Chrome/Firefox/**Safari** |
| 非同步支援 | 需 httpx | 困難 | ✅ 原生 async |
| 反偵測能力 | ❌ | 弱 | 強（可注入 JS） |
| 多頁面/多 Tab | ❌ | 複雜 | ✅ 原生支援 |
| API 易用性 | 最簡單 | 一般 | **很好** |

---

## 🏗️ Playwright 架構圖

```
你的程式碼
    │
    ▼
sync_playwright / async_playwright
    │
    ▼
Browser（瀏覽器實例：Chromium / Firefox / WebKit）
    │
    ▼
BrowserContext（獨立的 Session，有自己的 Cookie / Storage）
    │
    ▼
Page（一個 Tab）
    │
    ▼
Element（你要操作的 DOM 元素）
```

> 💡 **關鍵概念**：`BrowserContext` 就像「無痕視窗」，每個 Context 都有獨立的登入狀態。

---

## ❓ 沒有笨問題這回事

**Q：Playwright 是免費的嗎？**
> A：完全免費，由 Microsoft 開發並開源。Python、JS、Java、C# 都有支援。

**Q：一定要安裝真正的瀏覽器嗎？**
> A：是的，`playwright install` 會下載 Chromium、Firefox、WebKit，不用自己安裝 Chrome。

**Q：Playwright 和 Puppeteer 有什麼不同？**
> A：Puppeteer 只支援 Chrome，且主要是 JavaScript。Playwright 支援三種瀏覽器，且有多語言 SDK。

---

# 第二章：安裝與第一個程式

---

## 🔧 安裝步驟

```bash
# 1. 安裝 Python 套件
pip install playwright

# 2. 安裝瀏覽器（約 800MB，只需執行一次）
playwright install

# 3. 安裝 DataScout 的進階框架依賴
pip install loguru python-dotenv user-agents requests pillow
```

---

## 🔬 動手試試看：你的第一個 Playwright 程式

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 啟動 Chromium（headless=False = 你看得到瀏覽器視窗）
    browser = p.chromium.launch(headless=False)

    # 建立一個瀏覽器 Context
    context = browser.new_context()

    # 開啟新 Tab
    page = context.new_page()

    # 前往網頁，等到頁面完全載入
    page.goto("https://example.com")

    # 抓取頁面標題
    title = page.title()
    print(f"頁面標題：{title}")

    # 截圖存檔
    page.screenshot(path="screenshot.png", full_page=True)

    browser.close()
```

執行後你會看到瀏覽器開啟、前往 example.com，然後截圖儲存！

---

## 🧠 Brain Power

> 為什麼要用 `with sync_playwright() as p:` 這個語法？
> 如果不用 `with`，程式結束時瀏覽器會不會自動關閉？

---

# 第三章：導航與等待——網頁不是瞬間就好的

---

## 🚦 等待策略：你需要等到什麼？

```python
# 等待 DOM 解析完成（最快，但 JS 可能還沒跑）
page.goto(url, wait_until="domcontentloaded")

# 等待頁面 load 事件（圖片、樣式都載完）
page.goto(url, wait_until="load")

# 等待網路安靜（沒有 API 請求在跑，適合 SPA）
page.goto(url, wait_until="networkidle")   # ← 最穩但最慢
```

---

## 📋 等待元素的方法對照表

| 我想等... | 方法 | 說明 |
|-----------|------|------|
| 等某元素出現 | `page.wait_for_selector('#content')` | 等 DOM 出現 |
| 等某元素消失 | `page.wait_for_selector('.loading', state='hidden')` | 等 loading 結束 |
| 等網路請求 | `page.wait_for_load_state('networkidle')` | 等 AJAX 結束 |
| 等特定網址 | `page.wait_for_url('**/dashboard')` | 等導向完成 |
| 等時間 | `page.wait_for_timeout(2000)` | 等 2 秒（毫秒） |
| 等自訂條件 | `page.wait_for_function("document.title !== ''")`| 等 JS 條件成立 |

---

## 🔬 動手試試看：處理動態載入

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto("https://news.example.com", wait_until="domcontentloaded")

    # 等待文章列表出現（最多等 10 秒）
    page.wait_for_selector('.article-list', timeout=10000)

    # 現在可以安全地抓資料了
    articles = page.query_selector_all('.article-item')
    for article in articles:
        title = article.query_selector('h2').inner_text()
        link  = article.query_selector('a').get_attribute('href')
        print(f"{title} → {link}")

    browser.close()
```

---

## ⚠️ 常見陷阱：timeout 的單位是毫秒！

```python
# ✅ 正確：等 10 秒
page.wait_for_selector('#data', timeout=10000)

# ❌ 容易犯的錯誤：這樣只等 10 毫秒！
page.wait_for_selector('#data', timeout=10)
```

---

# 第四章：元素選擇與操作——真的在「點」網頁

---

## 🎯 兩種選擇器：CSS vs XPath

```python
# CSS Selector
element = page.query_selector('.product-title')
elements = page.query_selector_all('.product-item')

# XPath
element = page.query_selector('xpath=//h2[@class="title"]')
elements = page.query_selector_all('xpath=//div[contains(@class, "item")]')

# 推薦：用 locator（Playwright 新 API，更穩定）
locator = page.locator('.product-title')
locator = page.locator('xpath=//h2')
```

---

## 📋 元素操作對照表

| 操作 | 方法 | 說明 |
|------|------|------|
| 點擊 | `element.click()` | 模擬滑鼠點擊 |
| 輸入文字 | `element.fill('內容')` | 清除後輸入 |
| 逐字輸入 | `element.type('內容', delay=50)` | 模擬鍵盤打字 |
| 取得文字 | `element.inner_text()` | 取得可見文字 |
| 取得 HTML | `element.inner_html()` | 取得 innerHTML |
| 取得屬性 | `element.get_attribute('href')` | 取得任何屬性 |
| 截圖元素 | `element.screenshot(path='el.png')` | 只截這個元素 |
| 捲動到元素 | `element.scroll_into_view_if_needed()` | 讓元素進入視野 |
| 勾選 checkbox | `element.check()` / `.uncheck()` | 操作 checkbox |
| 選擇 select | `element.select_option('value')` | 操作下拉選單 |

---

## 🔬 動手試試看：填表單並送出

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://login.example.com")

    # 填入帳號密碼
    page.fill('#username', 'my_account')
    page.fill('#password', 'my_password')

    # 點擊登入按鈕
    page.click('#login-btn')

    # 等待導向完成
    page.wait_for_url('**/dashboard')
    print("登入成功！")

    # 確認登入後的用戶名稱
    username_display = page.query_selector('.user-name')
    if username_display:
        print(f"歡迎，{username_display.inner_text()}")

    browser.close()
```

---

## 🧠 Brain Power

> `page.fill()` 和 `page.type()` 都能輸入文字，哪一個更像真人？
> 什麼場景下你**必須**用 `type()` 而不是 `fill()`？

---

# 第五章：Session 管理——登入一次，用很多次

---

## 💡 核心概念：Storage State

登入後，網站把你的身份資訊存在：
- **Cookie**：`session_id`, `auth_token` 等
- **localStorage**：JWT Token、用戶設定
- **sessionStorage**：暫時資料

Playwright 可以把這些全部存起來，下次直接載入，**不用重新登入**！

---

## 🔬 動手試試看：保存與載入 Session

```python
# ===== 第一次執行：登入並儲存 Session =====
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://news.example.com/login")
    page.fill('#email', 'user@example.com')
    page.fill('#password', 'secret123')
    page.click('[type="submit"]')
    page.wait_for_url('**/home')

    # 儲存整個 Session（Cookie + localStorage）
    context.storage_state(path="session.json")
    print("Session 已儲存！")
    browser.close()


# ===== 之後執行：直接載入 Session =====
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # 載入之前儲存的 Session
    context = browser.new_context(storage_state="session.json")
    page = context.new_page()

    # 直接前往需要登入的頁面，不需要重新登入！
    page.goto("https://news.example.com/premium-article")
    content = page.query_selector('.article-content').inner_text()
    print(content[:200])

    browser.close()
```

---

## 📋 StorageManager（DataScout 框架）

DataScout 提供了更完整的 Session 管理工具：

```python
from playwright_base.storage.storage_manager import StorageManager

sm = StorageManager(storage_dir="data/storage")

# 儲存 Session
path = sm.save_storage_state(context, name="nikkei_session")

# 載入 Session
state = sm.load_storage_state("nikkei_session.json")

# 取得特定網域的 Cookie
cookies = sm.get_cookies_for_domain(state, ".nikkei.com")

# 合併兩個 Session 的 Cookie
merged = sm.merge_cookies(target_state, source_state)

# 列出所有已儲存的 Session
files = sm.list_storage_files()  # 按修改時間排序
```

---

# 第六章：反偵測——偽裝成真實使用者

---

## 🤖 為什麼網站知道你是機器人？

```
偵測方式                   正常使用者的值
─────────────────────    ─────────────────────────
navigator.webdriver      undefined（機器人是 true！）
navigator.plugins        有多個瀏覽器插件
navigator.languages      ['zh-TW', 'zh', 'en-US']
navigator.hardwareConcurrency  4~16 核心
滑鼠移動軌跡              有加速/減速，不是直線
點擊速度                  有隨機延遲
```

---

## 🛡️ 三層防禦策略

### 層級一：隱藏 webdriver 標記

```python
# 在每個頁面載入前注入 JavaScript
context.add_init_script("""
    // 隱藏 Playwright 的痕跡
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // 偽造插件列表
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer' }
        ]
    });

    // 設定語言
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-TW', 'zh', 'en-US', 'en']
    });
""")
```

### 層級二：隨機 User-Agent

```python
from playwright_base.anti_detection.user_agent_manager import UserAgentManager

uam = UserAgentManager(browser_type="chrome")

# 隨機選一個 Chrome User-Agent
ua = uam.get_random_user_agent()

# 分析這個 UA 的資訊
info = uam.analyze_user_agent(ua)
print(info)
# {'browser': 'Chrome', 'version': '120.0', 'os': 'Windows', 'mobile': False}

# 在 Context 中使用
context = browser.new_context(user_agent=ua)
```

### 層級三：模擬真人行為

```python
from playwright_base.anti_detection.human_like import HumanLikeBehavior

human = HumanLikeBehavior()

# 模擬人類滾動頁面（3~8 次，有閱讀停頓）
human.scroll_page(page)

# 模擬隨機滑鼠移動（有 20% 機率隨機點擊）
human.move_mouse_randomly(page)

# 模擬人類打字（每個字有延遲，5% 機率打錯再刪除）
human.type_humanly(page, '#search-box', '台積電股價')

# 隨機執行 1~3 個動作（滾動、移動、停頓）
human.perform_random_actions(page)
```

---

## 🔬 動手試試看：完整的反偵測啟動流程

```python
from playwright.sync_api import sync_playwright
import random, time

def create_stealth_browser():
    p = sync_playwright().start()

    browser = p.chromium.launch(
        headless=False,
        args=[
            '--start-maximized',
            '--disable-blink-features=AutomationControlled',  # 關鍵！
            '--no-sandbox',
        ]
    )

    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/123.0.0.0 Safari/537.36',
        locale='zh-TW',
        timezone_id='Asia/Taipei',
    )

    # 注入反偵測腳本
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        navigator.history_len = Math.floor(Math.random() * 3) + 2;
    """)

    page = context.new_page()
    return p, browser, page

p, browser, page = create_stealth_browser()
page.goto("https://bot.sannysoft.com")  # 測試反偵測效果的網站
page.screenshot(path="stealth_test.png", full_page=True)
browser.close()
p.stop()
```

---

## 📋 PlatformSpoofer（DataScout 框架）

```python
from playwright_base.anti_detection.platform_spoofer import PlatformSpoofer

spoofer = PlatformSpoofer()

# 產生隨機的瀏覽器指紋
fingerprint = spoofer.get_random_platform_fingerprint()
# {
#   'os': 'Windows 10',
#   'browser': 'Chrome 121',
#   'screen': {'width': 1920, 'height': 1080},
#   'hardware': {'cores': 8, 'memory': 16},
# }

# 套用到頁面（在 page 建立後）
spoofer.apply_spoof(page, fingerprint)
```

---

# 第七章：進階滑鼠模擬——貝茲曲線的魔法

---

## 🖱️ 為什麼滑鼠軌跡很重要？

真實的人移動滑鼠不是直線，而是**弧形曲線**。許多反機器人系統會分析滑鼠軌跡。

```
機器人的滑鼠軌跡：          真人的滑鼠軌跡：

A ─────────────→ B          A ～～～～～～→ B
  (完美直線)                  (有加速、減速、小抖動)
```

---

## 📐 貝茲曲線公式

DataScout 使用**二次貝茲曲線**計算滑鼠路徑：

```
位置 = (1-t)² × 起點 + 2(1-t)t × 控制點 + t² × 終點

其中 t 從 0 ~ 1，控制點是隨機偏移的中間點
```

```python
from playwright_base.anti_detection.advanced_detection import AdvancedAntiDetection
import asyncio

async def smooth_click(page, selector):
    aad = AdvancedAntiDetection()

    # 模擬人類行為（包含貝茲曲線滑鼠移動）
    await aad.simulate_human_behavior(page)

    # 在搜尋框模擬人類打字
    await aad.simulate_human_typing(page, '#search', '台灣半導體')

# 非同步版本使用方式
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://example.com")
        await smooth_click(page, '#search')
        await browser.close()

asyncio.run(main())
```

---

# 第八章：代理伺服器——換個 IP 繼續爬

---

## 🌐 為什麼需要代理？

```
你的 IP                      目標網站
──────────                   ──────────
123.456.789.0  →  請求 100 次  →  封鎖！
```

用代理伺服器：
```
你的電腦 → 代理1(IP-A) →  請求10次
         → 代理2(IP-B) →  請求10次  →  安全！
         → 代理3(IP-C) →  請求10次
```

---

## 📋 ProxyManager 使用方式

```python
from playwright_base.anti_detection.proxy_manager import ProxyManager

# 初始化（從 JSON 檔案載入代理清單）
pm = ProxyManager(
    proxies_file="proxies.json",
    test_url="https://httpbin.org/ip"
)

# 手動加入代理
pm.add_proxy({
    "server": "http://proxy1.example.com:8080",
    "username": "user",
    "password": "pass"
})

# 或從字串加入
pm.add_proxy_from_string("http://user:pass@proxy2.example.com:8080")

# 隨機選一個代理
proxy = pm.get_random_proxy()

# 循環輪換（第1次→代理1，第2次→代理2...）
proxy = pm.next_proxy()

# 測試代理是否可用
result = pm.test_proxy(proxy)  # 回傳 True/False

# 只取可用的代理
working = pm.get_working_proxies()

# 取得 Playwright 格式的代理設定
pw_proxy = pm.get_playwright_proxy()
# {'server': '...', 'username': '...', 'password': '...'}
```

---

## 🔬 動手試試看：搭配代理啟動瀏覽器

```python
with sync_playwright() as p:
    pm = ProxyManager(proxies_file="proxies.json")
    proxy = pm.get_playwright_proxy()

    browser = p.chromium.launch(headless=True)
    context = browser.new_context(proxy=proxy)
    page = context.new_page()

    page.goto("https://httpbin.org/ip")
    print(page.content())  # 確認 IP 是否已換

    browser.close()
```

---

# 第九章：錯誤處理——網站會反擊，你要應對

---

## 🚨 常見錯誤類型

| 錯誤 | 原因 | 解法 |
|------|------|------|
| **403 Forbidden** | 被識別為機器人 | 清 Cookie、換 UA、重試 |
| **TimeoutError** | 頁面太慢或元素不存在 | 增加 timeout、等待策略 |
| **Element not found** | 頁面結構改變 | 更新選擇器、加 wait |
| **網路錯誤** | 連線中斷 | 重試邏輯 |
| **CAPTCHA** | 觸發人機驗證 | 解 CAPTCHA 或降低速度 |
| **彈出視窗** | Cookie 同意、廣告 | 自動關閉彈窗 |

---

## 🛠️ ErrorHandler（DataScout 框架）

```python
from playwright_base.utils.error_handler import ErrorHandler

# 處理 403 錯誤（四步驟升級策略）
ErrorHandler.handle_403_error(page)
# 步驟1：清除所有 Cookie + 重載
# 步驟2：用 JS 修改 userAgent + 重載
# 步驟3：等待 5 秒 + 重試
# 步驟4：用瀏覽器內建 fetch() + 自訂 Headers 重試

# 處理「按住按鈕」驗證
ErrorHandler.handle_hold_button_verification(page)
# 找到按鈕 → 按住 8~10 秒 → 放開
```

---

## 🛠️ 自動彈窗處理

```python
from playwright_base.core.popup_handler import handle_popups, check_and_handle_popup

# 自動處理常見彈窗：
# - Cookie 同意按鈕（Accept / Agree / 同意）
# - Modal 關閉按鈕（Close / Dismiss / ×）
# - 付費牆（隱藏遮罩，恢復 overflow）
# - 歡迎頁面覆蓋層

was_handled = check_and_handle_popup(page)

# 或使用便利函式
handle_popups(
    page,
    auto_close_popups=True,
    custom_selectors=['.my-custom-modal .close-btn']
)
```

---

## 🔬 動手試試看：帶重試的完整爬蟲

```python
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def scrape_with_retry(url, max_retries=3):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for attempt in range(max_retries):
            try:
                print(f"第 {attempt+1} 次嘗試：{url}")
                page.goto(url, timeout=30000, wait_until="networkidle")

                # 等待關鍵元素出現
                page.wait_for_selector('.article-content', timeout=10000)

                content = page.query_selector('.article-content').inner_text()
                browser.close()
                return content

            except PlaywrightTimeout:
                print(f"超時！等待 {2**attempt} 秒後重試...")
                page.wait_for_timeout(2**attempt * 1000)

            except Exception as e:
                print(f"錯誤：{e}")
                if attempt == max_retries - 1:
                    raise

        browser.close()
        return None

result = scrape_with_retry("https://news.example.com/article/123")
```

---

# 第十章：多頁面與 iframe——Tab 管理

---

## 📑 管理多個 Tab

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()

    # 第一個 Tab
    page1 = context.new_page()
    page1.goto("https://google.com")

    # 第二個 Tab
    page2 = context.new_page()
    page2.goto("https://example.com")

    # 切換回第一個 Tab
    page1.bring_to_front()

    # 監聽新 Tab 開啟
    with context.expect_page() as new_page_info:
        page1.click('a[target="_blank"]')  # 點擊新分頁連結
    new_page = new_page_info.value
    new_page.wait_for_load_state()
    print(new_page.title())

    # 取得所有開啟的頁面
    all_pages = context.pages
    print(f"共 {len(all_pages)} 個 Tab")
```

---

## 🖼️ 處理 iframe

```python
page.goto("https://site-with-iframe.com")

# 方法一：用選擇器找 iframe
frame = page.frame_locator('iframe[src*="login"]')
frame.locator('#username').fill('user@example.com')
frame.locator('#password').fill('password')
frame.locator('[type="submit"]').click()

# 方法二：用 frame 名稱或 URL
frame = page.frame(url="**/auth/**")
frame.fill('#email', 'user@example.com')

# 登入後儲存 Session（跨 iframe 的 Cookie 也會儲存）
context.storage_state(path="session.json")
```

---

## 🧠 Brain Power

> Nikkei Asia 的登入表單在 iframe 裡，你要怎麼找到正確的 iframe？
> 試試用 `page.frames` 列出所有 iframe，再用 URL 來定位。

---

# 第十一章：CAPTCHA 處理——機器人的終極挑戰

---

## 🔒 常見 CAPTCHA 類型

| 類型 | 特徵 | 難度 |
|------|------|------|
| reCAPTCHA v2 | 「我不是機器人」勾選框 | 中 |
| reCAPTCHA v3 | 背景計分，無視覺介面 | 高 |
| hCaptcha | 圖片分類題 | 中 |
| 滑動驗證碼 | 滑塊拼圖 | 中 |
| 圖片識別 | 輸入圖片中的字 | 低~中 |
| 按住按鈕 | 長按 5~10 秒 | 低（可自動化） |

---

## 🛠️ 基本 CAPTCHA 處理

```python
from playwright_base.captcha_manager.captcha_solver.playwright_solver import PlaywrightCaptchaSolver

solver = PlaywrightCaptchaSolver()

# 自動偵測並嘗試處理 reCAPTCHA
result = solver.solve_recaptcha(page)

# 自動偵測並嘗試處理 hCaptcha
result = solver.solve_hcaptcha(page)

# 處理「按住按鈕」驗證（最容易自動化）
from playwright_base.utils.error_handler import ErrorHandler
ErrorHandler.handle_hold_button_verification(page)
```

---

## 💡 避免觸發 CAPTCHA 的策略

```python
import time, random

# 1. 控制請求速度（每次請求之間隨機等待）
def random_delay(min_sec=3, max_sec=8):
    wait = random.uniform(min_sec, max_sec)
    time.sleep(wait)

# 2. 隨機瀏覽行為（不要直接跳到目標頁面）
page.goto("https://news.example.com")      # 先到首頁
random_delay(2, 4)
page.click('.section-news')               # 點擊分類
random_delay(1, 3)
page.click('.article-link')               # 再點文章

# 3. 模擬閱讀（滾動頁面）
for _ in range(3):
    page.evaluate("window.scrollBy(0, 400)")
    random_delay(0.5, 1.5)
```

---

# 第十二章：PlaywrightBase——DataScout 的主角

---

## 🏗️ 框架架構

DataScout 的 `PlaywrightBase` 把前面學到的所有技術打包成一個好用的類別：

```
PlaywrightBase
├── start()              啟動瀏覽器
├── close()              關閉並清理
├── goto()               導航（帶 timeout 控制）
├── enable_stealth_mode() 注入反偵測腳本
├── save_storage()       儲存 Session
├── load_storage()       載入 Session
├── screenshot()         截圖
├── random_delay()       隨機等待
├── goto_url_with_retry()  帶重試+彈窗+錯誤處理的導航
└── register_page_event_handlers()  多頁面管理
```

---

## 🔬 動手試試看：使用 PlaywrightBase

```python
from playwright_base.core.base import PlaywrightBase

# 方式一：Context Manager（推薦）
with PlaywrightBase(headless=True, browser_type="chromium") as browser:
    browser.enable_stealth_mode()
    browser.goto("https://example.com")
    title = browser.page.title()
    print(title)
    browser.screenshot(path="result.png")


# 方式二：明確 start/close
browser = PlaywrightBase(
    headless=False,
    browser_type="chromium",
    storage_state="session.json",   # 載入已儲存的 Session
    viewport={'width': 1920, 'height': 1080},
    slow_mo=50                       # 每個操作慢 50ms，更像真人
)
browser.start()
browser.enable_stealth_mode()

# 帶重試、彈窗處理、錯誤恢復的導航
success = browser.goto_url_with_retry(
    "https://premium.example.com/article/123",
    max_retries=3,
    handle_popups=True,
    handle_errors=True
)

if success:
    content = browser.page.query_selector('.article').inner_text()
    print(content[:500])
    browser.save_storage("session_updated.json")

browser.close()
```

---

## 📋 DEFAULT_CONFIG 配置說明

```python
# playwright_base/config/settings.py
DEFAULT_CONFIG = {
    "browser": {
        "browser_type": "chromium",    # chromium / firefox / webkit
        "headless": False,             # 是否隱藏視窗
        "slow_mo": 0,                  # 操作延遲（毫秒）
    },
    "network": {
        "timeout": 30000,              # 元素等待 timeout（毫秒）
        "navigation_timeout": 60000,   # 頁面導航 timeout（毫秒）
        "retry": {"max_retries": 3},
        "wait_until": "networkidle",
    },
    "anti_detection": {
        "stealth_mode": True,
        "human_like_behavior": {
            "enabled": True,
            "scroll_probability": 0.7,
            "mouse_move_probability": 0.5,
        }
    },
    "page_management": {
        "max_pages": 3,               # 最多同時開幾個 Tab
        "auto_close_popups": True,
    },
    "screenshot": {
        "enabled": True,
        "on_error": True,             # 發生錯誤時自動截圖
        "save_path": "screenshots/",
        "full_page": True,
    }
}
```

---

# 第十三章：完整實戰——爬新聞網站付費文章

---

## 🎯 目標

爬取 Nikkei Asia 的文章列表（參考 DataScout 的真實範例）

---

## 📐 規劃流程

```
第一次執行                    之後執行
──────────                   ──────────
1. 開啟瀏覽器                1. 載入 session.json
2. 前往登入頁面              2. 直接前往搜尋頁
3. 填入帳密                  3. 搜尋關鍵字
4. 儲存 session.json         4. 翻頁抓文章
                             5. 進入文章頁
                             6. 抓取正文
```

---

## 💻 完整程式碼

```python
import json, time, random
from playwright.sync_api import sync_playwright
from playwright_base.core.popup_handler import handle_popups
from playwright_base.anti_detection.human_like import HumanLikeBehavior

STORAGE_FILE = "nikkei_session.json"
KEYWORDS = ["semiconductor", "Taiwan", "TSMC"]

def login_and_save():
    """第一次執行：手動登入後儲存 Session"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=['--start-maximized']
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/123.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        # 前往登入頁面
        page.goto("https://asia.nikkei.com")

        # 等待使用者手動登入（120 秒內）
        print("請在 120 秒內完成登入...")
        page.wait_for_url("**/dashboard**", timeout=120000)

        # 儲存 Session
        context.storage_state(path=STORAGE_FILE)
        print(f"Session 已儲存至 {STORAGE_FILE}")
        browser.close()


def scrape_articles(keyword, max_pages=3):
    """使用已儲存的 Session 爬文章"""
    human = HumanLikeBehavior()
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=STORAGE_FILE,  # 載入 Session
            viewport={'width': 1920, 'height': 1080},
        )
        page = context.new_page()

        for page_num in range(1, max_pages + 1):
            print(f"爬取關鍵字「{keyword}」第 {page_num} 頁...")

            search_url = (
                f"https://asia.nikkei.com/search?query={keyword}"
                f"&page={page_num}"
            )
            page.goto(search_url, wait_until="networkidle")

            # 處理彈出視窗
            handle_popups(page)

            # 模擬閱讀行為
            human.scroll_page(page)
            time.sleep(random.uniform(2, 4))

            # 找所有文章連結
            articles = page.query_selector_all('article.search-result, article[class*="Article"]')

            for article in articles:
                try:
                    title_el = article.query_selector('h2, h3, [class*="title"]')
                    link_el  = article.query_selector('a')

                    title = title_el.inner_text().strip() if title_el else ''
                    link  = link_el.get_attribute('href') if link_el else ''

                    if title and link:
                        results.append({
                            'keyword': keyword,
                            'page': page_num,
                            'title': title,
                            'url': f"https://asia.nikkei.com{link}" if link.startswith('/') else link
                        })
                except Exception as e:
                    print(f"解析文章時出錯：{e}")

            # 翻頁前的隨機等待
            time.sleep(random.uniform(3, 6))

        # 更新 Session（保持登入狀態有效）
        context.storage_state(path=STORAGE_FILE)
        browser.close()

    return results


# ===== 執行 =====
import os

if not os.path.exists(STORAGE_FILE):
    login_and_save()  # 第一次：需要登入

all_results = []
for kw in KEYWORDS:
    articles = scrape_articles(kw, max_pages=2)
    all_results.extend(articles)
    time.sleep(random.uniform(5, 10))  # 關鍵字之間多等一下

# 儲存結果
with open("nikkei_articles.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print(f"完成！共抓取 {len(all_results)} 篇文章資訊")
```

---

# 第十四章：Playwright 速查手冊

---

## 🗺️ 一頁搞定所有操作

```
啟動
├── sync_playwright() as p
├── p.chromium.launch(headless, args, slow_mo)
├── browser.new_context(storage_state, user_agent, proxy, viewport)
└── context.new_page()

導航
├── page.goto(url, timeout, wait_until)
├── page.reload()
├── page.go_back() / page.go_forward()
└── page.wait_for_url('**/pattern')

等待
├── page.wait_for_selector('#id', timeout)
├── page.wait_for_load_state('networkidle')
├── page.wait_for_timeout(milliseconds)
└── page.wait_for_function('JS 條件')

選擇元素
├── page.query_selector('.css')         → 單一元素
├── page.query_selector_all('.css')     → 多個元素
├── page.query_selector('xpath=//...')  → XPath
└── page.locator('.css')                → Locator API（推薦）

操作元素
├── element.click()
├── element.fill('text')
├── element.type('text', delay=50)
├── element.inner_text()
├── element.inner_html()
├── element.get_attribute('href')
├── element.check() / .uncheck()
├── element.select_option('value')
└── element.scroll_into_view_if_needed()

截圖 / 抓取
├── page.screenshot(path, full_page)
├── page.content()                      → 完整 HTML
├── page.evaluate('JS 程式碼')          → 執行 JS
└── page.pdf(path)                      → 轉 PDF

Session
├── context.storage_state(path)         → 儲存
├── browser.new_context(storage_state)  → 載入
└── context.clear_cookies()            → 清除

多頁面
├── context.new_page()
├── context.pages                       → 所有 Tab
├── page.bring_to_front()
└── page.frame_locator('iframe')
```

---

## 🏆 常見爬蟲場景

| 場景 | 關鍵技術 |
|------|---------|
| SPA 動態頁面 | `wait_for_load_state('networkidle')` |
| 需要登入 | `storage_state` 保存 Session |
| 被 403 封鎖 | 清 Cookie、換 UA、`ErrorHandler` |
| 有 iframe | `page.frame_locator('iframe[src*="..."]')` |
| 有分頁 | `following-sibling::a[1]` 或點「下一頁」 |
| 無限滾動 | 模擬滾動 + 等待新元素出現 |
| 需要截圖 | `page.screenshot(full_page=True)` |
| 要抓 PDF | `page.pdf(path='output.pdf')` |
| 多執行緒爬 | 每個 thread 獨立的 `BrowserContext` |

---

## ❓ 沒有笨問題這回事（總整理）

**Q：headless=True 和 headless=False 哪個比較不會被封鎖？**
> A：`headless=False` 更像真實使用者，但兩者用了反偵測腳本後差異不大。
> 正式環境通常用 `headless=True` 節省資源，但建議先用 `False` 開發和測試。

**Q：每次都要等 networkidle 嗎？會不會很慢？**
> A：不一定。`networkidle` 最穩但最慢（等所有 API 請求結束）。
> 如果你的目標元素在 `domcontentloaded` 後就出現，就用那個。
> 或者用 `wait_for_selector` 更精準地等你需要的元素。

**Q：Playwright 能跑在伺服器（無顯示器）上嗎？**
> A：可以！用 `headless=True` 就不需要顯示器。
> 或安裝 `Xvfb` 虛擬顯示器，就能跑 `headless=False`。

**Q：`query_selector` 和 `locator` 有什麼差？**
> A：`query_selector` 立即查找，元素不存在就回傳 `None`。
> `locator` 是惰性的，配合 `click()` 等操作才真正查找，且自動等待元素出現。
> 新專案推薦用 `locator`，更穩定。

---

## 🎓 你已經學會了

- [x] Playwright 核心架構（Browser → Context → Page）
- [x] 導航與智慧等待策略
- [x] 元素選擇（CSS / XPath / Locator）
- [x] 元素操作（點擊、輸入、取值）
- [x] Session 保存與載入
- [x] 三層反偵測策略（webdriver 隱藏、UA 輪換、真人行為模擬）
- [x] 貝茲曲線滑鼠軌跡
- [x] 代理伺服器管理
- [x] 錯誤處理與自動重試
- [x] 多 Tab 與 iframe 處理
- [x] CAPTCHA 基本應對策略
- [x] DataScout PlaywrightBase 框架使用
- [x] 完整實戰範例

---

> 📝 **最後提醒**：使用爬蟲前請確認網站的 `robots.txt` 和服務條款，
> 遵守合理的請求頻率，不要對網站造成過大負擔。
> 付費內容的爬取請確認自己有合法授權。🤖

---

*製作日期：2026-03-10 | 參考來源：[DataScout / playwright_base](https://github.com/jungyu/DataScout/tree/b81b6308c7aa63a953dcfdf30a7c40bce3a8e68e)*
