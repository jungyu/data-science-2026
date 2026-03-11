# 🧠 Head First XPath 學習手冊
### 用爬蟲視角，征服網頁資料！

> 📖 **參考來源**：[XPath Web Scraping Complete Guide](https://aaron.makiot.com/blogs/trick/2025/xpath-scraping-complete-guide/)

---

## 這本手冊適合誰？

✅ 想從網頁抓資料但看到 HTML 就頭暈的人
✅ 用過 `find()` 但覺得它有時候太笨的人
✅ 想讓爬蟲更精準、更有力的你

---

# 第一章：XPath 是什麼？你為什麼需要它？

---

## 🧩 先想一個問題

你打開一個商品頁面，HTML 長這樣：

```html
<div class="product-list">
  <div class="product-item">
    <h2>iPhone 15</h2>
    <span class="price">NT$ 32,900</span>
  </div>
  <div class="product-item">
    <h2>Samsung S24</h2>
    <span class="price">NT$ 28,000</span>
  </div>
</div>
```

**問題來了**：你要怎麼抓到所有的 `<h2>` 商品名稱？

> 🤔 用 CSS Selector？可以。
> 🤔 用 BeautifulSoup 的 `find_all`？也可以。
> 🤔 但如果條件很複雜、層級很深、屬性不固定呢？

**這時候，XPath 就是你的秘密武器。**

---

## 💡 XPath 的核心概念：它把 HTML 當成一棵樹

```
html
 └── body
      └── div.product-list
           ├── div.product-item
           │    ├── h2  ← "iPhone 15"
           │    └── span.price ← "NT$ 32,900"
           └── div.product-item
                ├── h2  ← "Samsung S24"
                └── span.price ← "NT$ 28,000"
```

XPath 就是告訴電腦：**「沿著這條路徑走，把我要的節點撿起來！」**

---

## 🧠 Brain Power

> 如果你要找「第二個商品的價格」，你會怎麼描述這條路徑？
> 先想想，再往下讀！

---

# 第二章：基本語法——從零開始選元素

---

## 📋 快速對照表：基本選擇器

| 我想要... | XPath 怎麼寫 | 說明 |
|-----------|-------------|------|
| 選所有 `<a>` 標籤 | `//a` | `//` = 從任何位置開始找 |
| 選 id 為 `main` 的元素 | `//*[@id='main']` | `@` = 屬性 |
| 選 class 包含 `btn` 的元素 | `//*[contains(@class, 'btn')]` | `contains()` = 部分匹配 |
| 選 class **完全等於** `btn` | `//*[@class='btn']` | 完整匹配，注意空格！ |
| 選某個屬性等於某值 | `//*[@href='https://example.com']` | 任何屬性都能這樣用 |

---

## 🔬 動手試試看

用 Python + lxml：

```python
from lxml import etree

html = """
<div>
  <a href="https://google.com" class="link external">Google</a>
  <a href="/about" class="link internal">關於我們</a>
  <button class="btn btn-primary">送出</button>
</div>
"""

tree = etree.fromstring(html)

# 選所有 <a>
links = tree.xpath('//a')
print([a.text for a in links])  # ['Google', '關於我們']

# 選 class 包含 'link' 的元素
links = tree.xpath('//*[contains(@class, "link")]')
print([el.text for el in links])  # ['Google', '關於我們']

# 選 href 屬性（加 @href 在最後）
hrefs = tree.xpath('//a/@href')
print(hrefs)  # ['https://google.com', '/about']
```

---

## ❓ 沒有笨問題這回事

**Q：`//a` 和 `/a` 有什麼差？**

> A：`//a` 表示「從整個文件的任何位置找 `<a>`」
> `/a` 表示「從當前節點的直接子節點找 `<a>`」
> 幾乎 99% 的情況你會用 `//`，除非你確定要從根開始走。

**Q：`@class='btn'` 和 `contains(@class, 'btn')` 哪個好用？**

> A：如果 class 是 `btn btn-primary`，用 `@class='btn'` 會**找不到**！
> 因為它要求完全相等。`contains()` 是你的好朋友。

---

# 第三章：階層關係——在家族樹中導航

---

## 🌳 家族關係圖

```
祖先 (ancestor)
   └── 父 (parent)
        ├── 自己 (self)
        │    ├── 子 (child)
        │    └── 子 (child)
        └── 兄弟 (sibling)
```

---

## 📋 階層選擇器對照表

| 關係 | XPath 寫法 | 範例 |
|------|-----------|------|
| 直接子元素 | `/parent/child` | `//ul/li` |
| 所有後代 | `//parent//descendant` | `//div//span` |
| 父元素 | `/..` | `//span/..` → 找 span 的父元素 |
| 祖先元素 | `/ancestor::tag` | `//span/ancestor::div` |
| 後面的兄弟 | `/following-sibling::tag` | `//h2/following-sibling::p` |
| 前面的兄弟 | `/preceding-sibling::tag` | `//h2/preceding-sibling::div` |

---

## 🎯 實戰場景：爬表格資料

```html
<table id="stock-data">
  <tr>
    <th>股票名稱</th>
    <th>現價</th>
    <th>漲跌</th>
  </tr>
  <tr>
    <td>台積電</td>
    <td>820</td>
    <td>+15</td>
  </tr>
  <tr>
    <td>鴻海</td>
    <td>105</td>
    <td>-2</td>
  </tr>
</table>
```

```python
# 所有資料列（跳過標題列）
rows = tree.xpath('//table[@id="stock-data"]//tr[position()>1]')

for row in rows:
    cells = row.xpath('.//td')  # 注意：用 . 代表「從當前節點開始」
    name  = cells[0].text
    price = cells[1].text
    change = cells[2].text
    print(f"{name}: {price} ({change})")

# 台積電: 820 (+15)
# 鴻海: 105 (-2)
```

---

## 🧠 Brain Power

> 如果我想找「某個 `<td>` 的前一個兄弟 `<td>`」，XPath 怎麼寫？

---

# 第四章：文字與內容過濾——找你想要的那個

---

## 📋 文字過濾對照表

| 我想要... | XPath 寫法 | 說明 |
|-----------|-----------|------|
| 文字包含某詞 | `[contains(text(), '關鍵字')]` | 部分匹配文字內容 |
| 文字完全相符 | `[text()='完整文字']` | 精確匹配 |
| 屬性值包含某詞 | `[contains(@class, 'active')]` | 用在 class 很好用 |
| 元素是空的 | `[not(node())]` | 找空元素 |
| 清除空白後比較 | `[normalize-space()='目標文字']` | 處理多餘空白 |

---

## ⚡ 常見陷阱：text() 的秘密

```html
<p>這是 <strong>重要的</strong> 文字</p>
```

```python
# ❌ 這樣找不到！因為 <p> 的直接文字節點只有「這是 」和「 文字」
tree.xpath('//p[text()="這是 重要的 文字"]')

# ✅ 用 normalize-space() 清除空白後比對
tree.xpath('//p[normalize-space()="這是 重要的 文字"]')

# ✅ 或用 contains()
tree.xpath('//p[contains(., "重要的")]')  # . 代表當前節點的所有文字
```

---

## 🎯 實戰場景：找特定連結

```python
# 找文字是「下一頁」的連結
next_page = tree.xpath('//a[text()="下一頁"]/@href')

# 找包含 "page" 的連結
page_links = tree.xpath('//a[contains(@href, "page")]/@href')

# 找 title 屬性包含 "詳細" 的按鈕
detail_btn = tree.xpath('//button[contains(@title, "詳細")]')
```

---

# 第五章：位置與索引——精準定位第幾個

---

## 📋 位置選擇器對照表

| 我想要... | XPath 寫法 | 說明 |
|-----------|-----------|------|
| 第一個 | `(//element)[1]` | XPath 索引從 **1** 開始，不是 0！ |
| 最後一個 | `(//element)[last()]` | `last()` 函式 |
| 第 N 個 | `(//element)[N]` | 例如第 3 個 = `[3]` |
| 倒數第 2 個 | `(//element)[last()-1]` | |
| 位置範圍 | `[position() > 2 and position() < 5]` | 選第 3、4 個 |
| 奇數位置 | `[position() mod 2 = 1]` | 用 mod 取餘數 |
| 偶數位置 | `[position() mod 2 = 0]` | |

---

## ⚠️ 超重要提醒：括號的位置！

```python
# ✅ 正確：先找所有 li，再取第一個
tree.xpath('(//li)[1]')

# ❌ 常見錯誤：這是找「第一個 ul 的第一個 li」，語意不同！
tree.xpath('//ul/li[1]')
```

---

## 🎯 實戰場景：分頁爬蟲

```html
<div class="pagination">
  <a href="/page/1">1</a>
  <a href="/page/2">2</a>
  <a href="/page/3">3</a>
  <a class="active" href="/page/4">4</a>
  <a href="/page/5">5</a>
</div>
```

```python
# 取得當前頁碼
current = tree.xpath('//div[@class="pagination"]/a[@class="active"]/text()')[0]

# 取得下一頁連結（當前頁的下一個兄弟）
next_url = tree.xpath('//a[@class="active"]/following-sibling::a[1]/@href')

# 取得最後一頁
last_url = tree.xpath('(//div[@class="pagination"]//a)[last()]/@href')

print(f"目前第 {current} 頁，下一頁：{next_url}")
```

---

# 第六章：複合條件——組合技讓你無所不能

---

## 📋 條件組合對照表

| 條件類型 | XPath 寫法 | 說明 |
|----------|-----------|------|
| AND（兩個都要） | `[@class='btn'][@disabled]` 或 `[@class='btn' and @disabled]` | 連續 `[]` 就是 AND |
| OR（任一即可） | `[@type='text' or @type='email']` | 用 `or` 關鍵字 |
| NOT（排除） | `[not(@class='hidden')]` | 用 `not()` 函式 |
| 多重過濾 | `[condition1][condition2][condition3]` | 依序過濾，越來越精準 |
| 聯集（兩組都要） | `//div | //span` | `|` = 合併兩個結果 |

---

## 🔬 動手試試看

```python
html = """
<form>
  <input type="text"     name="username" />
  <input type="password" name="password" />
  <input type="email"    name="email"    />
  <input type="submit"   value="送出"    />
  <input type="text"     name="phone"    disabled="disabled" />
</form>
"""

tree = etree.fromstring(html)

# 找所有文字或 email 輸入框
inputs = tree.xpath('//input[@type="text" or @type="email"]')
print([i.get('name') for i in inputs])  # ['username', 'email', 'phone']

# 找啟用中的文字輸入框（排除 disabled）
active = tree.xpath('//input[@type="text" and not(@disabled)]')
print([i.get('name') for i in active])  # ['username']

# 取得所有輸入框名稱聯集
all_names = tree.xpath('//input[@type="text"] | //input[@type="email"]')
```

---

## 🎯 實戰場景：精準抓商品

```python
# 抓「有折扣」且「有庫存」的商品
products = tree.xpath(
    '//div[contains(@class, "product")]'
    '[.//span[@class="discount"]]'   # 有折扣元素
    '[not(.//span[@class="sold-out"])]'  # 不是售完
)

# 抓標題或描述含「限定」的商品
limited = tree.xpath(
    '//div[contains(@class, "product")]'
    '[contains(.//h2/text(), "限定") or contains(.//p/text(), "限定")]'
)
```

---

# 第七章：特殊函式工具箱

---

## 📦 常用函式一覽

| 函式 | 用途 | 範例 |
|------|------|------|
| `text()` | 取文字節點 | `//h1/text()` |
| `contains(str, substr)` | 字串包含 | `contains(@class, 'btn')` |
| `normalize-space(str)` | 移除多餘空白 | `normalize-space(text())` |
| `count(nodeset)` | 計算數量 | `count(//li)` |
| `last()` | 最後一個位置 | `(//tr)[last()]` |
| `position()` | 當前位置 | `[position() > 1]` |
| `not(expr)` | 否定 | `not(@disabled)` |
| `starts-with(str, prefix)` | 開頭匹配 | `starts-with(@id, 'item-')` |
| `string-length(str)` | 字串長度 | `[string-length(@href) > 10]` |

---

## 🔬 動手試試看：計數與統計

```python
# 計算頁面上有幾個商品
count = tree.xpath('count(//div[@class="product-item"])')
print(f"共 {int(count)} 個商品")

# 找所有 id 以 "item-" 開頭的元素
items = tree.xpath('//*[starts-with(@id, "item-")]')

# 找文字長度超過 50 字的段落（用 Python 過濾比較實際）
paras = tree.xpath('//p')
long_paras = [p for p in paras if p.text and len(p.text) > 50]
```

---

# 第八章：動態頁面——JavaScript 渲染的挑戰

---

## 🚨 警告：XPath 找不到的情況

如果頁面是用 JavaScript 動態載入的，用 `requests` + `lxml` 會抓到**空的 HTML**！

```
你看到的頁面                  requests 抓到的
─────────────────           ────────────────────
<div class="product">       <div id="app"></div>
  <h2>iPhone 15</h2>        (JavaScript 還沒執行！)
  <span>NT$ 32,900</span>
</div>
```

---

## 💊 解決方案：搭配 Selenium

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

driver = webdriver.Chrome()
driver.get("https://example.com/products")

# 等待商品載入（最多 10 秒）
wait = WebDriverWait(driver, 10)
wait.until(EC.presence_of_element_located((By.XPATH, '//div[@class="product-item"]')))

# 用 XPath 找元素
products = driver.find_elements(By.XPATH, '//div[contains(@class, "product-item")]')
for p in products:
    name  = p.find_element(By.XPATH, './/h2').text
    price = p.find_element(By.XPATH, './/span[@class="price"]').text
    print(f"{name}: {price}")

driver.quit()
```

---

## 📋 動態頁面常見問題對照表

| 問題 | 原因 | 解法 |
|------|------|------|
| 元素找不到 | JS 尚未渲染 | `WebDriverWait` 等待出現 |
| 在 iframe 裡 | 框架隔離 | `driver.switch_to.frame()` |
| ID 每次不同 | 動態生成 | 用 `contains(@id, '穩定前綴')` |
| 資料來自 AJAX | 異步載入 | 等待特定元素出現後再抓 |
| 浮動元素擋住 | 覆蓋問題 | 找穩定的參考點，用 `following-sibling` |

---

# 第九章：完整實戰——爬一個電商頁面

---

## 🎯 目標

爬取一個電商網站的商品列表，包含：名稱、價格、評分、圖片網址

---

## 📐 規劃 XPath 路徑

```html
<!-- 假設的 HTML 結構 -->
<div class="product-grid">
  <div class="product-card" data-id="001">
    <img class="product-img" src="/images/item001.jpg" />
    <h3 class="product-name">無線藍牙耳機</h3>
    <div class="price-box">
      <span class="original-price">NT$ 2,000</span>
      <span class="sale-price">NT$ 1,500</span>
    </div>
    <div class="rating">
      <span class="stars">★★★★☆</span>
      <span class="review-count">(128)</span>
    </div>
  </div>
  <!-- 更多商品... -->
</div>
```

---

## 💻 完整爬蟲程式碼

```python
import requests
from lxml import etree

url = "https://example-shop.com/products"
headers = {'User-Agent': 'Mozilla/5.0 ...'}

resp = requests.get(url, headers=headers)
tree = etree.fromstring(resp.content, etree.HTMLParser())

# 找所有商品卡片
cards = tree.xpath('//div[contains(@class, "product-card")]')

results = []
for card in cards:
    # 商品 ID（從 data 屬性取）
    product_id = card.get('data-id')

    # 商品名稱
    name = card.xpath('.//h3[contains(@class, "product-name")]/text()')
    name = name[0].strip() if name else '未知'

    # 原價（可能沒有）
    original = card.xpath('.//span[@class="original-price"]/text()')
    original = original[0].strip() if original else None

    # 售價
    price = card.xpath('.//span[@class="sale-price"]/text()')
    price = price[0].strip() if price else '未知'

    # 評分
    stars = card.xpath('.//span[@class="stars"]/text()')
    stars = stars[0] if stars else ''

    # 評論數（去除括號）
    review_count = card.xpath('.//span[@class="review-count"]/text()')
    review_count = review_count[0].strip('()') if review_count else '0'

    # 圖片網址
    img_src = card.xpath('.//img[@class="product-img"]/@src')
    img_src = img_src[0] if img_src else ''

    results.append({
        'id': product_id,
        'name': name,
        'original_price': original,
        'sale_price': price,
        'rating': stars,
        'reviews': review_count,
        'image': img_src,
    })

# 輸出結果
for item in results:
    print(f"[{item['id']}] {item['name']} | {item['sale_price']} | {item['rating']}")
```

---

# 第十章：XPath 速查手冊

---

## 🗺️ 一頁搞定所有 XPath

```
選擇器類型
├── 基本
│   ├── //tag              → 所有 tag 元素
│   ├── //*                → 所有元素
│   ├── //tag[@attr]       → 有某屬性的 tag
│   ├── //tag/@attr        → 取屬性值
│   └── //tag/text()       → 取文字
│
├── 屬性過濾
│   ├── [@id='value']
│   ├── [@class='value']           ← 精確匹配
│   ├── [contains(@class,'value')] ← 部分匹配（推薦）
│   ├── [starts-with(@id,'prefix')]
│   └── [@href]                    ← 只要有這個屬性
│
├── 文字過濾
│   ├── [text()='完整文字']
│   ├── [contains(text(),'部分')]
│   └── [normalize-space()='清除空白後比對']
│
├── 階層導航
│   ├── /child             → 直接子元素
│   ├── //descendant       → 所有後代
│   ├── /..                → 父元素
│   ├── /ancestor::tag     → 指定祖先
│   ├── /following-sibling::tag  → 後面兄弟
│   └── /preceding-sibling::tag → 前面兄弟
│
├── 位置索引
│   ├── [1]                → 第一個（從1開始！）
│   ├── [last()]           → 最後一個
│   ├── [last()-1]         → 倒數第二
│   └── [position()>2]     → 位置大於2
│
└── 條件組合
    ├── [cond1][cond2]     → AND
    ├── [a or b]           → OR
    ├── [not(cond)]        → NOT
    └── //a | //b          → 聯集
```

---

## 🏆 常見爬蟲場景 XPath

| 場景 | XPath |
|------|-------|
| 所有表格資料列 | `//table[@id='data']//tr[position()>1]` |
| 商品列表 | `//div[contains(@class, 'product-item')]` |
| 分頁連結 | `//div[contains(@class, 'pagination')]//a` |
| 導覽選單 | `//nav//li/a` |
| 文章段落 | `//div[@id='content']//p` |
| 所有圖片 | `//img/@src` |
| 圖集圖片 | `//div[contains(@class, 'gallery')]//img/@src` |
| 下拉選單選項 | `//select[@id='options']/option` |
| 下一頁按鈕 | `//a[text()='下一頁' or @aria-label='Next']` |
| 麵包屑 | `//nav[@aria-label='breadcrumb']//a` |

---

## ❓ 沒有笨問題這回事（總整理）

**Q：什麼時候用 XPath，什麼時候用 CSS Selector？**
> A：CSS Selector 簡單、直觀，適合大部分場景。
> XPath 強在「往上找父層」、「用文字內容過濾」、「條件組合」。
> 遇到複雜情況，XPath 幾乎都能解。

**Q：lxml 和 BeautifulSoup 都能用 XPath 嗎？**
> A：**lxml** 完整支援 XPath。
> **BeautifulSoup** 原生不支援 XPath，但可以搭配 lxml 的 parser。
> **Selenium** 用 `find_elements(By.XPATH, '...')` 支援 XPath。

**Q：XPath 的效能怎麼樣？**
> A：XPath 在靜態 HTML 解析（lxml）速度非常快，幾乎感受不到差異。
> 在 Selenium 中，等待 JavaScript 渲染才是效能瓶頸，不是 XPath。

**Q：`.//tag` 和 `//tag` 的差別？**
> A：`.//tag` = 從**當前節點**開始找
> `//tag` = 從**整個文件根**開始找
> 在 loop 裡處理子元素時，一定要用 `.//`！

---

## 🎓 你已經學會了

- [x] XPath 的核心概念（DOM 樹形結構）
- [x] 基本選擇器（tag、屬性、class）
- [x] 階層導航（父、子、兄弟、祖先）
- [x] 文字與內容過濾（text、contains、normalize-space）
- [x] 位置索引（第幾個、最後一個、範圍）
- [x] 複合條件（AND、OR、NOT、聯集）
- [x] 特殊函式（count、starts-with、string-length）
- [x] 動態頁面處理（Selenium + WebDriverWait）
- [x] 完整實戰案例

---

> 📝 **最後提醒**：爬蟲前請確認網站的 `robots.txt` 和使用條款，
> 適度控制請求頻率，做個有禮貌的爬蟲工程師！🤖

---

*製作日期：2026-03-10 | 資料來源：[XPath Scraping Complete Guide](https://aaron.makiot.com/blogs/trick/2025/xpath-scraping-complete-guide/)*
