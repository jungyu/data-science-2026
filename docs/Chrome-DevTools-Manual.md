# 🔍 Head First：用 Chrome DevTools 讀懂任何網站

> **你的任務不是「把畫面截圖下來」**
> 你的任務是：**「找到資料從哪裡來、怎麼來、長什麼樣子」**

---

> 📌 **這本手冊給誰看？**
> 給還沒開始寫爬蟲程式，但想用肉眼先把網站資料流搞清楚的你。
> 在你打第一行程式碼之前，DevTools 就是你的解剖刀。

---

## 🗺️ 全書地圖

| 章節 | 主題 |
|------|------|
| 第 0 章 | 打開 DevTools，認識整個操作介面 |
| 第 1 章 | Elements — 看 DOM、認識 HTML 結構 |
| 第 2 章 | Console — 用瀏覽器當計算機和驗證工具 |
| 第 3 章 | Network — 找到資料真正的來源 |
| 第 4 章 | Application — Cookie、Storage、Token 藏在哪 |
| 第 5 章 | Request & Response 完整解讀 |
| 第 6 章 | 用 Postman 呼叫 API：GET / POST / PUT / PATCH / DELETE |

---

---

# 第 0 章｜打開 DevTools，認識整個操作介面

## 0.1 打開 DevTools 的三種方式

| 方式 | Mac | Windows |
|------|-----|---------|
| 快捷鍵 | `⌥ Option + ⌘ Cmd + I` | `Ctrl + Shift + I` |
| 右鍵選單 | 對頁面任意位置右鍵 → **Inspect** | 同左 |
| 選單列 | Chrome 右上角 `⋮` → More tools → Developer tools | 同左 |

> 💡 **建議：** 習慣快捷鍵，你一天會開關它幾十次。

---

## 0.2 DevTools 的整體版面

```
┌─────────────────────────────────────────────────────────────────┐
│  Elements │ Console │ Sources │ Network │ Application │ ...     │  ← 分頁列
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│          主工作區（各分頁的內容顯示在這裡）                         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Console 抽屜（可隨時按 Esc 叫出，不佔用主分頁）                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 0.3 最常用的 5 個分頁 — 先記這 5 個就夠了

### 📌 Elements
- **你能做什麼：** 看 HTML 結構（DOM）、修改顏色/文字做測試、找 CSS 樣式
- **爬蟲用途：** 找目標資料在 HTML 哪個節點，確認它的屬性名稱

### 📌 Console
- **你能做什麼：** 執行 JavaScript、印出資料、驗證你寫的 selector 對不對
- **爬蟲用途：** 在真實頁面上即時測試，不用寫程式就能驗證邏輯

### 📌 Network
- **你能做什麼：** 看瀏覽器送出了哪些 HTTP 請求、拿到了什麼回應
- **爬蟲用途：** **最重要的一頁** — 找到資料真正從哪個 API 來的

### 📌 Application
- **你能做什麼：** 看 Cookies、LocalStorage、SessionStorage
- **爬蟲用途：** 了解登入狀態、找 token、找 API Key

### 📌 Sources
- **你能做什麼：** 看網站的 JS 原始碼、設中斷點除錯
- **爬蟲用途：** 逆向找 API endpoint 藏在哪段 JS 裡（進階技巧）

---

## 0.4 調整 DevTools 位置

DevTools 預設停靠在右側或下方，你可以調整：

1. DevTools 右上角 `⋮`（三個點）→ **Dock side**
2. 選擇：靠右 / 靠下 / **獨立視窗**（建議雙螢幕用）

> 💡 **建議：** 學習階段把 DevTools 調成「獨立視窗」，網站和工具並排更好操作。

---

---

# 第 1 章｜Elements — 讀懂 DOM，找到資料的位置

## 1.1 DOM 到底是什麼？

> **DOM（Document Object Model）= 瀏覽器把 HTML 解析成「樹狀結構」**

你在瀏覽器看到的每一個文字、圖片、按鈕，在 DOM 裡都是一個「節點」（Node）。

**HTML 原始碼 vs DOM 的差異：**

```
HTML 原始碼（你寫的）             DOM（瀏覽器解析後）
────────────────────             ──────────────────────
<div class="card">              ▼ div.card
  <h2>商品名稱</h2>      →          ▼ h2
  <span class="price">              "商品名稱"
    $299                           ▼ span.price
  </span>                            "$299"
</div>
```

**關鍵觀念：**

```
⚠️ JS 可以動態新增/修改 DOM！
   所以你「檢視頁面原始碼」看到的 HTML
   ≠ DevTools Elements 看到的 DOM

   Elements 顯示的是「當前真實狀態」，原始碼是「最初狀態」。
```

---

## 1.2 用滑鼠定位任何元素

### 方法 A：右鍵 → Inspect（最直覺）

1. 對你感興趣的元素（文字、圖片、按鈕）**右鍵**
2. 選 **Inspect**
3. Elements 面板會自動跳到對應的 HTML 節點，並**高亮顯示**

### 方法 B：用選取工具（最精準）

1. DevTools 左上角的 **箭頭圖示**（快捷鍵：`Ctrl+Shift+C` / `Cmd+Shift+C`）
2. 滑鼠移到頁面，懸停在哪個元素，DOM 就跟著高亮
3. 點一下，Elements 立刻定位過去

---

## 1.3 Elements 面板的兩個區塊

```
┌──────────────────────────────────────────────────────┐
│  ▼ <html>                                            │
│    ▼ <body>                                          │  ← 左側：DOM 樹
│      ▼ <div class="container">                       │
│          <h1>標題</h1>                               │
│          <p class="desc">說明文字</p>                │
├──────────────────────────────────────────────────────┤
│  Styles │ Computed │ Event Listeners │ ...           │  ← 右側/下方：屬性面板
│                                                      │
│  .desc {                                             │
│    color: #333;                                      │
│    font-size: 14px;                                  │
│  }                                                   │
└──────────────────────────────────────────────────────┘
```

**左側 DOM 樹操作：**

| 動作 | 說明 |
|------|------|
| 點 `▶` 展開節點 | 看子元素 |
| 雙擊屬性值 | 直接在瀏覽器裡修改（測試用，不影響原始碼） |
| 右鍵節點 | Copy selector / Copy XPath / Copy outerHTML |
| `Delete` 鍵 | 暫時刪除節點（測試版面用） |

---

## 1.4 認識 HTML 節點的屬性

每個 HTML 節點可能有這些屬性，都可以用來定位：

```html
<div
  id="product-123"              ← id（頁面唯一，最穩定）
  class="card featured"         ← class（可能動態改變）
  data-testid="product-card"    ← data-* 屬性（工程師加的，通常很穩定）
  data-product-id="456"         ← data-* 帶資料（爬蟲金礦）
  aria-label="商品卡片"          ← 無障礙屬性（也可用）
>
```

**定位穩定度排名（爬蟲視角）：**

```
最穩定 ──────────────────────────────── 最不穩定
  id  >  data-*  >  aria  >  結構  >  class  >  nth-child
```

---

## 1.5 Copy XPath：用但要改

在 Elements 節點上右鍵 → Copy → Copy XPath

你通常會得到這種「自動生成」的 XPath：

```
/html/body/div[3]/main/section[2]/div[1]/div[2]/h2
```

**問題：**
- 任何 HTML 結構變動就斷掉
- 完全看不出語意，不知道在找什麼

**改造成穩定版：**

```
//*[@data-testid='product-title']
```

或是：

```
//h2[contains(@class, 'product-name')]
```

> 📐 **原則：越短越語意越好，越長越結構越脆**

---

## 1.6 常用 XPath 模板（收藏這頁）

| 目的 | XPath 寫法 |
|------|------------|
| 找有特定 attribute 的元素 | `//*[@data-testid='price']` |
| 找特定文字內容的按鈕 | `//button[contains(., '加入購物車')]` |
| 找某 div 下所有連結 | `//div[@id='result-list']//a` |
| 找文字精確符合 | `//h1[text()='首頁']` |
| 找父節點 | `//span[contains(., '特價')]/ancestor::div[1]` |
| 找下一個兄弟節點 | `//label[contains(., '姓名')]/following-sibling::input[1]` |

---

---

# 第 2 章｜Console — 瀏覽器裡的即時實驗室

## 2.1 Console 是什麼？

Console 讓你在**當前頁面的環境**裡，直接執行 JavaScript。

這代表你可以：
- 立刻測試「這個 selector 找不找得到東西」
- 把頁面上的資料用 JS 抓出來印在螢幕上
- 不寫任何程式，就驗證你的邏輯

---

## 2.2 打開 Console 的方式

- 點 DevTools 上方 **Console** 分頁
- **或** 在其他分頁按 `Esc` → 底部出現 Console 抽屜（不用切換分頁）

---

## 2.3 Console 基本操作

**輸入指令後按 Enter 執行**

```javascript
// 印出文字
console.log("hello")

// 算數
2 + 3    // 回傳 5

// 取得頁面標題
document.title

// 取得目前網址
location.href
```

**多行指令：** 按 `Shift + Enter` 換行，最後 `Enter` 執行

---

## 2.4 用 Console 驗證 CSS Selector

```javascript
// 找第一個符合的元素
document.querySelector(".product-title")
// 回傳：<h2 class="product-title">商品名稱</h2>  ← 如果找到
// 回傳：null  ← 如果找不到

// 找所有符合的元素
document.querySelectorAll(".product-card")
// 回傳：NodeList(12) [div.product-card, ...]

// 確認數量
document.querySelectorAll(".product-card").length
// 回傳：12

// 取出文字內容
document.querySelector(".price").textContent
// 回傳："$299"

// 取出 href 屬性
document.querySelector("a.more-link").getAttribute("href")
// 回傳："/products/123"
```

---

## 2.5 用 Console 驗證 XPath

DevTools 提供內建的 `$x()` 函數：

```javascript
// 找所有符合 XPath 的元素
$x("//h2[@class='product-title']")

// 取文字（搭配 map）
$x("//h2[@class='product-title']").map(el => el.textContent)
// 回傳：["商品A", "商品B", "商品C"]

// 確認數量
$x("//div[@data-testid='product-card']").length
```

> ✅ **黃金法則：在真實頁面上驗到 selector 確實有回傳資料，才是真的可用。**

---

## 2.6 Console 的 $ 快捷指令

DevTools 在 Console 裡提供幾個快捷：

| 指令 | 等同於 | 說明 |
|------|--------|------|
| `$("selector")` | `document.querySelector()` | 找第一個 |
| `$$("selector")` | `document.querySelectorAll()` | 找全部 |
| `$x("xpath")` | 自訂 XPath 查詢 | 找符合 XPath 的元素 |
| `$0` | — | 上一個在 Elements 裡點選的元素 |
| `$_` | — | 上一個運算的結果 |

---

---

# 第 3 章｜Network — 找到資料真正的來源

> 🏆 **Network 是爬蟲分析裡最重要的分頁。**
> 你眼睛看到的資料，90% 都是從某個 API 請求來的。
> 找到那個請求，你就找到資料的源頭。

---

## 3.1 Network 面板的基本概念

每當瀏覽器要取得任何東西（HTML、圖片、資料、字型），都會發出一個 **HTTP Request（請求）**。

Network 面板就是把這些請求**全部記錄下來**讓你看。

```
你輸入網址 → 瀏覽器發出大量 Request：
  ├── GET https://example.com/          ← HTML 主頁面
  ├── GET https://example.com/style.css ← 樣式
  ├── GET https://example.com/app.js    ← JavaScript
  ├── GET https://api.example.com/products?page=1  ← 資料 API ✨
  └── GET https://example.com/logo.png  ← 圖片
```

---

## 3.2 Network 面板操作準備

**在開始分析前，先做這三步設定：**

### ① 勾選 Preserve log
```
位置：Network 面板工具列 → 勾選 "Preserve log"
作用：頁面跳轉後，舊的請求記錄不會消失
```

### ② 勾選 Disable cache
```
位置：Network 面板工具列 → 勾選 "Disable cache"
作用：強制每次都重新載入，不用快取，看到最真實的請求
```

### ③ 重新整理頁面
```
快捷鍵：F5（普通重整）或 Ctrl+Shift+R / Cmd+Shift+R（強制重整）
作用：從頭觸發所有請求，讓 Network 記錄完整
```

---

## 3.3 Network 面板的 5 個欄位

| 欄位 | 意思 |
|------|------|
| **Name** | 請求的資源名稱（通常是 URL 最後一段） |
| **Status** | HTTP 狀態碼（200=成功, 404=找不到, 403=禁止） |
| **Type** | 資源類型（document, fetch, xhr, img, script...） |
| **Size** | 回應大小 |
| **Time** | 請求花多久 |

---

## 3.4 用 Filter 快速找到 API 請求

Network 上方有 **Filter 工具列：**

```
All │ Fetch/XHR │ JS │ CSS │ Img │ Media │ Font │ Doc │ WS │ Wasm │ Other
```

**爬蟲最常用的篩選方式：**

| 做法 | 說明 |
|------|------|
| 點 **Fetch/XHR** | 過濾出 API 呼叫（最常見的資料來源） |
| 搜尋欄輸入 `api` | 找 URL 包含 api 的請求 |
| 搜尋欄輸入 `json` | 找回應類型是 json 的 |
| 搜尋欄輸入 `search` | 找搜尋相關的 API |
| 搜尋欄輸入 `graphql` | 找 GraphQL API |

> 💡 **SPA 網站（如 React/Vue 做的）一定有大量 Fetch/XHR 請求，資料就藏在那裡。**

---

## 3.5 點進一個 Request：你要看的 5 個子頁籤

點擊任何一個請求，右側（或下方）出現詳細資訊面板：

```
Headers │ Payload │ Preview │ Response │ Initiator │ Timing
```

### 📋 Headers（最重要，先看這裡）

分成兩大區塊：

**General（概覽）**
```
Request URL:   https://api.example.com/v1/products     ← Endpoint！
Request Method: GET                                     ← 用哪個 HTTP Method
Status Code:    200 OK                                  ← 成功了嗎
```

**Request Headers（你送出去的）**
```
Accept:          application/json
Authorization:   Bearer eyJhbGciOiJIUzI1NiJ9...       ← 有帶 Token！
Content-Type:    application/json
Cookie:          session_id=abc123; user_token=xyz      ← Cookie
User-Agent:      Mozilla/5.0 ...
```

**Query String Parameters（GET 的參數）**
```
page:     1
limit:    20
keyword:  手機
sort:     price_asc
```

### 📦 Payload（POST/PUT 才有）

```json
{
  "username": "aaron",
  "password": "secret123"
}
```
這是你**送出去的 request body**，通常是 JSON 格式。

### 👁️ Preview（最直觀）

DevTools 幫你把 JSON 排列整齊，可以展開/收合，**快速掃瞄資料結構**。

### 📄 Response（原始回應）

```json
{
  "status": "success",
  "data": {
    "items": [...],
    "total": 156,
    "page": 1
  }
}
```
看到這個就代表你找到了真正的資料！

### ⏱️ Timing

顯示請求各階段花了多少時間，如果 API 很慢或被限速，這裡會顯現出來。

### 🔗 Initiator

顯示是哪段 JS 觸發了這個請求，進階分析 token 生成邏輯時用。

---

## 3.6 Copy as cURL：把請求變成可複製的指令

在 Network 列表的任何一筆請求上 **右鍵** → **Copy** → **Copy as cURL**

你會拿到類似這樣的指令：

```bash
curl 'https://api.example.com/v1/products?page=1&limit=20' \
  -H 'Authorization: Bearer eyJhbGciOiJI...' \
  -H 'Accept: application/json' \
  -H 'Cookie: session_id=abc123'
```

**為什麼這很重要？**

> 把這段 cURL 貼到終端機跑得通 = 你已確認這個請求「不靠瀏覽器就能成立」。
> 這就是你爬蟲的最小可重現單元。

---

## 3.7 解讀常見 HTTP 狀態碼

| 狀態碼 | 意思 | 爬蟲解讀 |
|--------|------|----------|
| **200** | OK，成功 | ✅ 資料拿到了 |
| **201** | Created，建立成功 | ✅ POST/PUT 成功 |
| **301 / 302** | 重新導向 | 注意最終落點 URL |
| **400** | Bad Request | 你的請求參數有問題 |
| **401** | Unauthorized | 需要登入 / Token 失效 |
| **403** | Forbidden | 沒有權限，可能被擋 |
| **404** | Not Found | 資源不存在 |
| **429** | Too Many Requests | 被限速了，慢下來 |
| **500** | Server Error | 伺服器出錯，稍後再試 |

---

---

# 第 4 章｜Application — 身份驗證資訊藏在哪？

## 4.1 為什麼要看 Application 面板？

很多 API 需要你帶上「身份憑證」才能拿到資料，這些憑證通常存在：

- **Cookies**：最傳統的登入狀態儲存方式
- **LocalStorage**：現代網站常用來存 token
- **SessionStorage**：關掉頁面就消失的暫存

---

## 4.2 Cookies

```
位置：Application → Storage → Cookies → 選擇網站 domain
```

**重要欄位解讀：**

| 欄位 | 說明 |
|------|------|
| Name | Cookie 名稱（如：`session_id`, `auth_token`） |
| Value | Cookie 的值（可能是 JWT Token 或 session ID） |
| Domain | 這個 Cookie 適用哪個網域 |
| Expires | 什麼時候過期 |
| HttpOnly | 有打勾 = JS 無法讀取（安全機制） |
| Secure | 有打勾 = 只在 HTTPS 傳送 |

**爬蟲用法：**
- 找到 `session`、`token`、`auth` 相關的 Cookie
- 在發出 API 請求時帶上這些 Cookie，就能模擬已登入狀態

---

## 4.3 LocalStorage

```
位置：Application → Storage → Local Storage → 選擇網站 domain
```

現代 SPA 網站（React/Vue/Angular）常把 **JWT Token** 存在 LocalStorage：

```
Key: access_token
Value: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM...
```

這個 token 通常需要放在 API 請求的 Header：
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 4.4 JWT Token 的秘密

如果你發現一個很長的 token 長這樣：

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

它是一個 **JWT（JSON Web Token）**，由三段 Base64 組成，中間用 `.` 隔開：

```
Header.Payload.Signature
```

你可以到 **https://jwt.io** 把它貼上去解碼，看看裡面包含什麼資訊（過期時間、使用者 ID 等）。

---

---

# 第 5 章｜Request & Response 完整解讀

## 5.1 一次完整的 HTTP 通訊長什麼樣子

```
    你（Client）                          伺服器（Server）
        │                                        │
        │  ──────── HTTP Request ────────────►  │
        │                                        │
        │  Request Line:  GET /api/products HTTP/1.1
        │  Headers:       Host: api.example.com
        │                 Authorization: Bearer token123
        │                 Accept: application/json
        │  Body:          （GET 沒有 body）
        │                                        │
        │  ◄─────── HTTP Response ──────────── │
        │                                        │
        │  Status Line:  HTTP/1.1 200 OK
        │  Headers:      Content-Type: application/json
        │                Cache-Control: max-age=300
        │  Body:         {"data": [...]}
        │                                        │
```

---

## 5.2 Request 的結構拆解

一個 HTTP Request 由四個部分組成：

### ① Request Line（第一行）
```
GET /api/v1/products?page=1&limit=20 HTTP/1.1
 ↑          ↑                           ↑
Method     Path + Query String        HTTP版本
```

### ② Request Headers（元資料，告訴伺服器「你是誰、要什麼格式」）

```
Host:            api.example.com          ← 目標主機
Accept:          application/json         ← 我要 JSON 格式
Accept-Language: zh-TW,zh;q=0.9          ← 我要繁體中文
Authorization:   Bearer eyJhbGci...       ← 我的身份驗證
Content-Type:    application/json         ← 我送的 body 是 JSON（POST 才有意義）
User-Agent:      Mozilla/5.0 ...          ← 我是什麼瀏覽器/程式
Cookie:          session_id=abc; token=xyz ← Cookie
Referer:         https://example.com/     ← 從哪個頁面來的
```

### ③ 空行
分隔 Headers 與 Body。

### ④ Request Body（只有 POST / PUT / PATCH 才有）
```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```

---

## 5.3 Response 的結構拆解

### ① Status Line（第一行）
```
HTTP/1.1 200 OK
          ↑   ↑
        狀態碼  狀態訊息
```

### ② Response Headers（伺服器告訴你「這個回應的相關資訊」）

```
Content-Type:     application/json; charset=utf-8  ← 回應格式
Content-Length:   1523                              ← 回應大小
Cache-Control:    max-age=3600                      ← 可以快取多久
Set-Cookie:       session_id=xyz; HttpOnly          ← 要你存的 Cookie
Access-Control-Allow-Origin: *                      ← CORS 設定
X-RateLimit-Remaining: 98                          ← 還剩幾次 API 呼叫
```

### ③ Response Body（真正的內容）
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "iPhone 15",
        "price": 29900,
        "stock": 50
      }
    ],
    "pagination": {
      "page": 1,
      "total_pages": 8,
      "total_items": 156,
      "next": "/api/v1/products?page=2"
    }
  }
}
```

---

## 5.4 讀懂 JSON Response：找到你要的資料

拿到 JSON 後，你要問自己這幾個問題：

```
✅ 資料列表在哪一個 key 下？
   → 這裡在 data.items

✅ 分頁資訊在哪裡？
   → data.pagination.next / data.pagination.page

✅ 這一頁有幾筆？總共幾筆？
   → items.length vs data.pagination.total_items

✅ 每筆資料的唯一識別是什麼？
   → id 欄位

✅ 還有沒有下一頁？
   → data.pagination.next 不是 null/undefined 就有
```

---

## 5.5 常見 JSON 結構模式

### 模式 A：直接陣列
```json
[
  {"id": 1, "name": "商品A"},
  {"id": 2, "name": "商品B"}
]
```

### 模式 B：包在 data 裡
```json
{
  "data": [
    {"id": 1, "name": "商品A"}
  ],
  "meta": {"total": 100}
}
```

### 模式 C：results + count（Django REST Framework 常見）
```json
{
  "count": 100,
  "next": "https://api.example.com/items/?page=2",
  "previous": null,
  "results": [...]
}
```

### 模式 D：Cursor-based pagination
```json
{
  "data": [...],
  "cursor": {
    "next_cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true
  }
}
```

---

---

# 第 6 章｜用 Postman 呼叫 API：GET / POST / PUT / PATCH / DELETE

> 🎯 **這一章的目標：**
> 不用寫任何程式，用 Postman 這個工具，親手呼叫 API，確認資料怎麼來的。

---

## 6.1 Postman 是什麼？

**Postman** 是一個專門用來測試 API 的工具。

你在 DevTools Network 找到了 API endpoint，接下來可以：
- 用 Postman 直接呼叫那個 API
- 修改參數看看回應怎麼變化
- 帶上不同的 Headers（Token/Cookie）
- 測試 GET / POST / PUT / PATCH / DELETE 各種操作

**官網：** [https://www.postman.com/](https://www.postman.com/)

---

## 6.2 安裝與第一次啟動

1. 前往 [https://www.postman.com/downloads/](https://www.postman.com/downloads/)
2. 下載對應系統版本安裝
3. 可以選擇登入建立帳號（免費），或直接「Skip and go to the app」

**介面認識：**

```
┌─────────────────────────────────────────────────────────────┐
│  File  Edit  View  ...               [New] [Import]         │
├───────────┬─────────────────────────────────────────────────┤
│           │  ● GET    │ https://api.example.com/products    │  ← URL 列
│ 我的請求  │  ─────────────────────────────────────────────── │
│ 收藏列表  │  Params │ Authorization │ Headers │ Body        │  ← 請求設定
│           │                                                  │
│           │  ─────────────────────────────────────────────── │
│           │  Body  Cookies  Headers  Test Results           │  ← 回應區
│           │  { "data": [...] }                              │
└───────────┴─────────────────────────────────────────────────┘
```

---

## 6.3 HTTP Methods 的意義與用途

在開始操作前，先理解每個 Method 代表什麼：

| Method | 語意 | 用途 | 有 Request Body？ |
|--------|------|------|------------------|
| **GET** | 取得 | 讀取資料，不改動任何東西 | ❌ 沒有 |
| **POST** | 新增 | 建立新資料 | ✅ 有 |
| **PUT** | 完整更新 | 用新資料**整個替換**舊資料 | ✅ 有 |
| **PATCH** | 部分更新 | 只更新**指定欄位** | ✅ 有 |
| **DELETE** | 刪除 | 刪除指定資源 | 通常沒有 |

**REST API 設計慣例：**

```
資源：/api/v1/products

GET    /api/v1/products          → 取得商品列表
GET    /api/v1/products/123      → 取得單一商品
POST   /api/v1/products          → 新增商品
PUT    /api/v1/products/123      → 完整替換商品 123
PATCH  /api/v1/products/123      → 部分更新商品 123
DELETE /api/v1/products/123      → 刪除商品 123
```

---

## 6.4 實作：GET 請求

GET 是最常見的操作，用來讀取資料。

### 步驟

1. 點 **New** → **HTTP Request**（或點 `+` 開新分頁）
2. Method 選 **GET**
3. 在 URL 欄位輸入 endpoint

```
https://jsonplaceholder.typicode.com/posts
```

4. 點 **Send**

### 加上 Query Parameters

很多 GET API 需要帶參數，在 **Params** 頁籤填入：

| Key | Value |
|-----|-------|
| `_page` | `1` |
| `_limit` | `10` |

Postman 會自動組合成：
```
https://jsonplaceholder.typicode.com/posts?_page=1&_limit=10
```

### 加上 Headers

在 **Headers** 頁籤新增：

| Key | Value |
|-----|-------|
| `Authorization` | `Bearer your_token_here` |
| `Accept` | `application/json` |

### 看 Response

回應區可以切換：
- **Body → Pretty**：格式化的 JSON（最好讀）
- **Body → Raw**：原始文字
- **Headers**：伺服器回應的 Headers

---

## 6.5 實作：POST 請求（新增資料）

POST 用來建立新資料，需要帶 **Request Body**。

### 步驟

1. Method 選 **POST**
2. URL 輸入：`https://jsonplaceholder.typicode.com/posts`
3. 點 **Body** 頁籤
4. 選 **raw** → 右側下拉選 **JSON**
5. 輸入 Body：

```json
{
  "title": "我的新文章",
  "body": "這是文章內容",
  "userId": 1
}
```

6. 點 **Send**

**預期回應（201 Created）：**
```json
{
  "id": 101,
  "title": "我的新文章",
  "body": "這是文章內容",
  "userId": 1
}
```

---

## 6.6 實作：PUT 請求（完整更新）

PUT 用新的完整資料**取代**既有資源。

### 步驟

1. Method 選 **PUT**
2. URL 輸入：`https://jsonplaceholder.typicode.com/posts/1`（注意：URL 包含 ID）
3. Body 選 raw → JSON，輸入**完整的新資料**：

```json
{
  "id": 1,
  "title": "更新後的標題（完整替換）",
  "body": "更新後的內容（完整替換）",
  "userId": 1
}
```

4. 點 **Send**

> ⚠️ **PUT 的特性：** 你沒有送的欄位，伺服器可能會刪除或置空。
> 所以 PUT 要送**所有欄位**。

---

## 6.7 實作：PATCH 請求（部分更新）

PATCH 只更新你指定的欄位，其他欄位保持原樣。

### 步驟

1. Method 選 **PATCH**
2. URL 輸入：`https://jsonplaceholder.typicode.com/posts/1`
3. Body 選 raw → JSON，只輸入**要改的欄位**：

```json
{
  "title": "只改標題，其他不動"
}
```

4. 點 **Send**

> ✅ **PATCH vs PUT：**
> - PATCH：「我只想改這幾個欄位」
> - PUT：「我要用全新資料替換整筆記錄」

---

## 6.8 實作：DELETE 請求（刪除）

### 步驟

1. Method 選 **DELETE**
2. URL 輸入：`https://jsonplaceholder.typicode.com/posts/1`
3. 通常不需要 Body
4. 點 **Send**

**常見回應：**

```json
{}
```
或是 `204 No Content`（空回應，代表刪除成功）

---

## 6.9 設定 Authorization（帶 Token）

很多 API 需要身份驗證，在 Postman 有三種常見方式：

### 方式 A：Bearer Token（最常見）
- 點 **Authorization** 頁籤
- Type 選 **Bearer Token**
- 輸入 token 值

Postman 自動加上 Header：`Authorization: Bearer your_token`

### 方式 B：API Key
- Type 選 **API Key**
- Key：`x-api-key`（視 API 而定）
- Value：你的 API Key
- Add to：Header 或 Query Params

### 方式 C：手動加 Header
- 點 **Headers** 頁籤
- 自己加上 `Authorization` → `Bearer your_token`

---

## 6.10 匯入 cURL：從 DevTools 到 Postman 一步搞定

你在 DevTools 複製了 cURL 指令？可以直接匯入 Postman！

### 步驟

1. Postman 點 **Import**（左上角）
2. 選 **Raw text** 頁籤
3. 貼上 cURL 指令
4. 點 **Import**

Postman 自動幫你填好 URL、Headers、Body——**完全不用手動一個個輸入。**

> 🚀 **工作流程：**
> DevTools Network → Copy as cURL → Postman Import → 直接測試 ✅

---

## 6.11 儲存請求到 Collections

測試完一個 API，記得儲存：

1. 點 **Save**（右上角）
2. 取一個名字（例如：「取得商品列表」）
3. 選擇或建立一個 **Collection**（類似資料夾，可以依專案分類）

**好處：**
- 下次直接從側邊欄點開，不用重新輸入
- 可以把整個 Collection 分享給同學或同事

---

## 6.12 從 DevTools 到 Postman：完整工作流程

```
① 打開 Chrome DevTools → Network
          ↓
② 操作網站，觸發資料載入
          ↓
③ 在 Fetch/XHR 找到資料 API 請求
          ↓
④ 點進請求，記錄：
   - Request URL
   - Method（GET/POST...）
   - Query Parameters
   - Request Headers（特別是 Authorization / Cookie）
   - Request Body（如果有）
          ↓
⑤ Copy as cURL
          ↓
⑥ Postman Import → 自動填入
          ↓
⑦ 點 Send，確認同樣能拿到資料
          ↓
⑧ 修改參數（換 page、換 keyword），觀察回應變化
          ↓
⑨ 你已完全理解這支 API 的行為！
```

---

---

# 附錄 A｜貼牆上的 SOP 清單

```
□ 打開 DevTools（Option+Cmd+I / Ctrl+Shift+I）
□ Network → 勾 Preserve log + Disable cache
□ 重新整理頁面
□ 篩選 Fetch/XHR
□ 找到回應是 JSON 的請求
□ 點進去看：URL / Method / Params / Headers / Response
□ Copy as cURL → Postman Import
□ 在 Postman 確認能獨立取得資料
□ 修改參數，了解 API 的規律
□ 解讀 JSON 結構，找到資料列表和分頁邏輯
```

---

# 附錄 B｜DevTools 快捷鍵速查

| 功能 | Mac | Windows |
|------|-----|---------|
| 開啟/關閉 DevTools | `Option+Cmd+I` | `Ctrl+Shift+I` |
| 元素選取模式 | `Cmd+Shift+C` | `Ctrl+Shift+C` |
| 開啟 Console 抽屜 | `Esc` | `Esc` |
| 強制重新整理 | `Cmd+Shift+R` | `Ctrl+Shift+R` |
| 清除 Network 記錄 | `Cmd+K` | `Ctrl+L` |
| 搜尋所有 Network 請求 | `Cmd+F` | `Ctrl+F` |

---

# 附錄 C｜練習用公開 API

這些 API 不需要帳號，可以直接用 Postman 練習：

| API | 說明 | 網址 |
|-----|------|------|
| JSONPlaceholder | 假資料 CRUD API（posts / users / todos） | https://jsonplaceholder.typicode.com |
| Dog CEO | 隨機狗狗圖片 | https://dog.ceo/api/breeds/image/random |
| Open-Meteo | 免費天氣 API | https://open-meteo.com/en/docs |
| GitHub API | GitHub 公開資料 | https://api.github.com/users/octocat |
| Punk API | 啤酒資料（練習 query params） | https://punkapi.com/documentation/v2 |

---

> 📘 **完成這本手冊後，你已經能夠：**
> - 用 DevTools Elements 讀懂任何網頁的 HTML 結構
> - 用 Console 驗證你的元素定位邏輯
> - 用 Network 找到資料真正的 API 來源
> - 解讀 HTTP Request 和 Response 的每個部分
> - 用 Postman 呼叫 GET、POST、PUT、PATCH、DELETE API
>
> **下一步：** 用程式把你在 DevTools 裡看到的，自動化執行。