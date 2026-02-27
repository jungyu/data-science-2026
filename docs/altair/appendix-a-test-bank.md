# Appendix A：測驗題庫

> Altair → Vega-Lite → Next.js 產品化 完整題庫 v1.0

---

## 使用說明

- 本題庫涵蓋六週課程的核心知識
- 題型分為：選擇題（A）、是非題（B）、短答題（C）、讀 Spec/改 Spec 題（D）、實作題（E）
- 每題標註建議週次，可依需求抽題做小考、期中或期末評量
- 附有參考答案與解析

### 週次出題建議

| 週次 | 建議題目 |
|------|---------|
| 第 1 週 | A1, A2, B2, C1 |
| 第 2 週 | A3, A4, C3, D1 |
| 第 3 週 | D2, D3, C2 |
| 第 4 週 | A5, D4, C4 |
| 第 5 週 | A6, A7, B4, E2 |
| 第 6 週 | B5, E3（或口試題） |

---

## A. 選擇題

> 每題 2 分

### A1（單選）｜第 1 週

Altair 的核心思想最接近下列哪一項？

- A. 告訴電腦每一步怎麼畫
- B. 宣告圖表規格，描述資料如何映射到視覺
- C. 直接把圖片畫在 Canvas 上
- D. 把資料轉成 SVG 再手刻 DOM

**答案：B**

**解析：** Altair 是 declarative（宣告式），核心在 encoding 與 spec，而非逐步指令繪圖。A 是 matplotlib 的做法，C 和 D 都是更底層的手動操作方式。

---

### A2（單選）｜第 1 週

Vega-Lite spec 裡，最常負責「資料欄位 → 視覺通道」的是哪個區塊？

- A. mark
- B. data
- C. encoding
- D. config

**答案：C**

**解析：** `encoding` 定義資料欄位如何映射到視覺通道（x、y、color、size 等）。`mark` 定義圖表類型，`data` 提供資料來源，`config` 控制全域樣式。

---

### A3（多選）｜第 2 週

下列哪些屬於 Vega-Lite spec 中常見的頂層欄位？

- A. encoding
- B. transform
- C. router
- D. layer

**答案：A、B、D**

**解析：** `encoding`、`transform`、`layer` 都是 Vega-Lite spec 的合法頂層欄位。`router` 是 Next.js 的概念，不存在於 Vega-Lite 中。

---

### A4（單選）｜第 2 週

想把圖從直條圖改成折線圖，最直接該改哪個欄位？

- A. data
- B. mark
- C. encoding
- D. transform

**答案：B**

**解析：** `mark` 決定圖表的視覺標記類型。將 `"mark": "bar"` 改成 `"mark": "line"` 就能從長條圖變成折線圖，不需要改動其他欄位。

---

### A5（多選）｜第 4 週

「把 spec 存到 DB 再由 Next.js 渲染」的優點有哪些？

- A. 前後端解耦、可獨立演進
- B. spec 可版本控管、可 diff
- C. 前端一定會比較快
- D. AI 更容易操作（改 JSON 即可）

**答案：A、B、D**

**解析：** 前後端解耦（A）、spec 可版本化（B）、AI 可操作 JSON（D）是 spec 驅動架構的核心優勢。C 是錯誤的——速度取決於資料量和渲染引擎，不一定更快。

---

### A6（單選）｜第 5 週

在 Next.js 中使用 Vega/React-Vega 時，常需要把圖表元件設定為 client component 的原因是：

- A. Vega 需要 DOM/瀏覽器環境
- B. Next.js 不支援 JSON
- C. React 不支援 SVG
- D. API route 只能跑在 client

**答案：A**

**解析：** Vega 渲染引擎需要操作 DOM（建立 SVG 或 Canvas 元素），而 Next.js 的 Server Component 在伺服器端執行，沒有 DOM 環境。因此必須使用 `"use client"` 標記。

---

### A7（單選）｜第 5 週

哪一種做法比較符合「產品化」與「可維運」？

- A. Notebook 產圖 → 截圖貼到網站
- B. Python 直接輸出 PNG → 前端顯示 img
- C. 產 Vega-Lite spec（JSON）→ 前端渲染
- D. 把 Altair embed HTML 放 iframe

**答案：C**

**解析：** Spec 驅動的架構（C）保留了圖表的結構化資訊，支援互動、版本控管、AI 操作。其他方式都會喪失圖表的語意和互動能力。

---

### A8（多選）｜第 3 週

下列哪些是「宣告式視覺化（declarative）」的特徵？

- A. 可用 JSON 描述
- B. 方便做 schema 驗證
- C. 更適合做 diff/版本控管
- D. 一定比 imperative 更細緻可控

**答案：A、B、C**

**解析：** 宣告式視覺化的優勢在於結構化（A）、可驗證（B）、可版本化（C）。D 是錯誤的——imperative 方式（如 matplotlib）在某些場景下提供更精細的像素級控制。

---

## B. 是非題

> 每題 1 分

### B1 ｜第 1 週

Altair 產出的 Vega-Lite spec 只會在 Python 裡使用，離開 Python 就無法渲染。

**答案：F（錯誤）**

**解析：** Vega-Lite spec 是 JSON 格式，可以在任何支援 Vega-Lite 的環境中渲染，包括瀏覽器（JavaScript）、Node.js，甚至 R 語言。這正是 IR 的價值所在。

---

### B2 ｜第 1 週

Vega-Lite 的 encoding 主要描述資料欄位如何映射到 x/y/color/size 等通道。

**答案：T（正確）**

**解析：** encoding 是 Vega-Lite 的核心概念，定義了資料欄位（field）到視覺通道（channel）的映射關係，包括 x、y、color、size、shape、opacity、tooltip 等。

---

### B3 ｜第 3 週

把圖表規格存成 JSON 後，可用 git 追蹤變更並做 code review。

**答案：T（正確）**

**解析：** JSON 是純文字格式，git 可以精確追蹤每次修改的差異。這與 PNG 等二進位格式不同——PNG 的 diff 只能做像素比對，無法理解語意變化。

---

### B4 ｜第 5 週

react-vega 能 SSR（server-side render）完整輸出圖表，不需要 DOM。

**答案：F（錯誤）**

**解析：** Vega 渲染引擎需要 DOM/Canvas 環境來產生視覺輸出。在 Next.js 中，Vega 元件必須標記為 `"use client"`，在瀏覽器中執行。

---

### B5 ｜第 6 週

AI 修改圖表時，「改 spec」通常比「叫 AI 直接畫圖」更可治理。

**答案：T（正確）**

**解析：** 修改 JSON spec 是精確的、可驗證的、可追蹤的、可回滾的。而「AI 直接畫圖」意味著 AI 要生成程式碼並執行，結果是不透明的圖片，無法審查和控制。

---

## C. 短答題

> 每題 5 分（建議 3-5 句作答）

### C1 ｜第 1 週

**請用自己的話解釋「Altair 是 Authoring tool，Vega-Lite 是 IR，Next.js 是 Renderer」的意思。**

**參考答案要點：**

- **Altair**（撰寫工具）：用 Python 快速建立圖表，產生規格文件。就像用 Word 寫文件。
- **Vega-Lite**（中介表示）：圖表的 JSON 規格，是可保存、可傳輸、可版本化的結構化描述。就像 PDF 是文件的標準格式。
- **Next.js**（渲染器）：根據規格在瀏覽器中呈現互動式圖表。就像 PDF 閱讀器負責顯示 PDF。
- **核心價值**：三者解耦，各自獨立演進。產生規格的工具（Python/R/JS）、規格本身（JSON）、渲染引擎（瀏覽器），可以分別替換而不影響其他層。

---

### C2 ｜第 3 週

**為什麼「spec 驅動」比「輸出 PNG 圖檔」更適合做互動式產品？**

**參考答案要點：**

- Spec 保留了圖表的語意（encoding、tooltips、selection），前端可以渲染互動式圖表
- PNG 只是像素的集合，失去了所有結構和互動能力
- Spec 可以搭配不同資料重複使用（換資料源即可）
- Spec 可以被前端動態調整（主題、尺寸），PNG 無法
- Spec 支援 tooltip、縮放、選取等互動功能

---

### C3 ｜第 2 週

**請舉例說明「同一份資料」可以用哪些 encoding 方式造成不同解讀？（至少 2 個例子）**

**參考答案要點：**

- **x 軸類型**：`year:O`（有序分類）均勻排列 vs `year:Q`（數值）按比例排列，後者可能隱藏不等距年份
- **y 軸起點**：`scale: {zero: false}` 可能誇大數值差異，讓小幅變動看起來很劇烈
- **color 映射**：用 `nominal`（分類色）vs `quantitative`（漸層色）表示同一個數值欄位，傳達完全不同的訊息
- **聚合方式**：`sum` vs `mean` 可能得出相反的結論（總量大 vs 平均差）
- **排序方式**：按字母排序 vs 按值排序，影響讀者對「最重要品類」的判斷

---

### C4 ｜第 4 週

**如果 AI 產出的 spec 有問題（欄位不存在、type 錯誤），你會怎麼讓系統更可靠？列出 3 個方法。**

**參考答案要點：**

1. **JSON Schema 驗證**：使用 Vega-Lite 官方 JSON Schema 驗證 spec 的結構合法性
2. **資料集合約（Dataset Contract）**：維護欄位白名單和型別定義，在 AI 修改後檢查 encoding 中的 field 是否存在於 data 中
3. **Spec 驗證器（Validator）**：自訂驗證函數檢查 mark 類型、encoding type、scale 設定等
4. **Fallback 機制**：如果驗證失敗，回退到修改前的 spec
5. **Human-in-the-loop**：AI 修改後先預覽，人工確認後才存入

---

## D. 讀 Spec / 改 Spec 題

> 每題 8 分

### D1（讀 spec）｜第 2 週

給定 spec：

```json
{
  "mark": "bar",
  "encoding": {
    "x": {"field": "year", "type": "ordinal"},
    "y": {"field": "sales", "type": "quantitative"}
  }
}
```

問題：

1. 這是什麼圖？
2. 哪個欄位決定 x 軸的資料？
3. 如果要改成橫向長條圖，應如何改？

**參考答案：**

1. **長條圖**（垂直長條圖 / 直條圖）
2. `encoding.x.field` → `"year"` 欄位決定 x 軸的資料
3. 交換 x 和 y 的 encoding：
   ```json
   "encoding": {
     "x": {"field": "sales", "type": "quantitative"},
     "y": {"field": "year", "type": "ordinal"}
   }
   ```

---

### D2（改 spec）｜第 3 週

把下列折線圖改成「折線 + 點」的組合圖，並加入 tooltip 顯示 year 與 sales。

原始 spec：
```json
{
  "mark": "line",
  "encoding": {
    "x": {"field": "year", "type": "ordinal"},
    "y": {"field": "sales", "type": "quantitative"}
  }
}
```

**參考答案：**

使用 `layer` 疊加折線和點，並在 encoding 中加入 tooltip：

```json
{
  "layer": [
    {
      "mark": "line",
      "encoding": {
        "x": {"field": "year", "type": "ordinal"},
        "y": {"field": "sales", "type": "quantitative"}
      }
    },
    {
      "mark": "point",
      "encoding": {
        "x": {"field": "year", "type": "ordinal"},
        "y": {"field": "sales", "type": "quantitative"},
        "tooltip": [
          {"field": "year", "type": "ordinal"},
          {"field": "sales", "type": "quantitative"}
        ]
      }
    }
  ]
}
```

或使用簡化寫法（mark 帶 point 參數）：

```json
{
  "mark": {"type": "line", "point": true},
  "encoding": {
    "x": {"field": "year", "type": "ordinal"},
    "y": {"field": "sales", "type": "quantitative"},
    "tooltip": [
      {"field": "year", "type": "ordinal"},
      {"field": "sales", "type": "quantitative"}
    ]
  }
}
```

---

### D3（找 bug）｜第 3 週

以下 spec 中，如果 year 是 2020、2021、2022，sales 是數字，這份 spec 可能有什麼問題？

```json
{
  "mark": "line",
  "encoding": {
    "x": {"field": "year", "type": "quantitative"},
    "y": {"field": "sales", "type": "ordinal"}
  }
}
```

**參考答案：**

1. **year 的 type 應為 `ordinal` 或 `temporal`**：標記為 `quantitative` 會讓 Vega-Lite 把年份當作連續數值處理，產生帶小數的軸刻度（如 2020.5），且間距按比例計算而非等距
2. **sales 的 type 應為 `quantitative`**：標記為 `ordinal` 會讓 Vega-Lite 把銷售額當作分類處理，無法正確呈現數值的大小關係和比例
3. **兩者的 type 完全顛倒了**：year 是類別/時間維度，應為 ordinal 或 temporal；sales 是連續數值，應為 quantitative

---

### D4（產品化題）｜第 4 週

你要做一個 chart gallery：DB 存 spec，前端渲染。請說明 API 回傳內容最少需要哪些欄位？（至少 4 個）

**參考答案：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | UUID | 唯一識別碼，用於 API 路由和引用 |
| `name` | String | 圖表名稱，用於顯示和搜尋 |
| `spec` | JSON | Vega-Lite 規格，前端渲染用 |
| `created_at` | Timestamp | 建立時間，用於排序和追蹤 |
| `description` | String | 圖表說明（選填但建議有） |
| `updated_at` | Timestamp | 更新時間（選填但對版本管理重要） |
| `tags` | String[] | 分類標籤（選填，方便篩選） |

最少需要前四個欄位才能構成一個可運作的 chart gallery。

---

## E. 實作題

> 每題 15 分，可當週作業或期末練習

### E1（Altair → spec）｜第 3 週

給定任意 CSV 資料（學生自選），要求：

1. 用 Altair 做一張圖表（需包含 color 或 tooltip 其一）
2. 用 `chart.to_dict()` 匯出 `spec.json`
3. 在報告中解釋：mark、encoding、data 各欄位的作用

**評分標準：**
- 圖表正確產生（5 分）
- spec.json 結構完整（5 分）
- 解釋清楚且正確（5 分）

---

### E2（spec → Next.js render）｜第 5 週

給定一份 spec.json：

1. 建立 Next.js 頁面讀取此 spec
2. 使用 react-vega 或 vega-embed 渲染
3. 說明為何需要 client component（`"use client"`）

**評分標準：**
- Next.js 專案正確建立（3 分）
- 圖表成功渲染（7 分）
- 說明正確（5 分）

---

### E3（AI patch）｜第 6 週

給定原 spec，要求學生寫出一個修改方案（可以是 JSON Patch 或自訂格式）完成：

1. line → bar
2. 加上 tooltip
3. 存成 patch.json

並在報告中說明 patch 的契約（哪些操作可以做，哪些不行）。

**評分標準：**
- Patch 格式正確（5 分）
- 修改結果正確（5 分）
- 契約說明合理（5 分）

---

## F. 口試題（加分/鑑別度高）

### F1

> 你的系統如何避免 AI 產生「誤導性圖表」？

**評分要點：**
- 提到 Schema 驗證（基本）
- 提到長條圖 y 軸從 0 開始的規則（中等）
- 提到人工審核機制（human-in-the-loop）（中等）
- 提到自動化檢測（如 scale.zero 檢查）（進階）
- 提到圖表設計原則（如 Tufte 的 data-ink ratio）（進階）

---

### F2

> 如果 5 年後要換前端圖表引擎（Vega → ECharts），你如何保護既有資料與 spec？

**評分要點：**
- 認識到 spec 是 JSON，可以轉換格式（基本）
- 提到寫 spec converter（Vega-Lite → ECharts option）（中等）
- 提到保持 data 和 spec 分離的架構優勢（中等）
- 提到只需要改渲染層，API 和 DB 不受影響（進階）
- 提到 IR 的本質就是讓上下游解耦（進階）

---

### F3

> 你會如何設計 ChartSpec 的 versioning（向下相容）？

**評分要點：**
- 提到用版本號追蹤修改（基本）
- 提到 chart_versions 表設計（中等）
- 提到 JSON diff 記錄每次變化（中等）
- 提到 migration 策略（spec v1 → v2 的轉換腳本）（進階）
- 提到向下相容的 fallback 渲染（進階）

---

## 附錄：快速出題對照表

| 題號 | 類型 | 難度 | 週次 | 考核能力 |
|------|------|------|------|---------|
| A1 | 選擇 | 易 | 1 | Declarative 概念 |
| A2 | 選擇 | 易 | 1 | Spec 結構理解 |
| A3 | 多選 | 中 | 2 | Spec 欄位知識 |
| A4 | 選擇 | 易 | 2 | Mark 概念 |
| A5 | 多選 | 中 | 4 | 產品化架構理解 |
| A6 | 選擇 | 中 | 5 | Next.js + Vega 整合 |
| A7 | 選擇 | 中 | 5 | 產品化思維 |
| A8 | 多選 | 中 | 3 | Declarative 特性 |
| B1 | 是非 | 易 | 1 | IR 跨平台特性 |
| B2 | 是非 | 易 | 1 | Encoding 概念 |
| B3 | 是非 | 中 | 3 | 版本控管理解 |
| B4 | 是非 | 中 | 5 | SSR 限制理解 |
| B5 | 是非 | 中 | 6 | AI 可治理性 |
| C1 | 短答 | 中 | 1 | 三層架構理解 |
| C2 | 短答 | 中 | 3 | Spec vs 圖片比較 |
| C3 | 短答 | 難 | 2 | Encoding 影響分析 |
| C4 | 短答 | 難 | 4 | AI 安全性設計 |
| D1 | 讀 spec | 易 | 2 | Spec 閱讀能力 |
| D2 | 改 spec | 中 | 3 | Spec 修改能力 |
| D3 | 找 bug | 中 | 3 | Type 系統理解 |
| D4 | 設計 | 難 | 4 | API 設計能力 |
| E1 | 實作 | 中 | 3 | Altair 實作 |
| E2 | 實作 | 難 | 5 | 全端整合 |
| E3 | 實作 | 難 | 6 | AI Patch 設計 |
| F1 | 口試 | 難 | 6 | 安全性思維 |
| F2 | 口試 | 難 | 綜合 | 架構彈性思維 |
| F3 | 口試 | 難 | 綜合 | 版本設計能力 |

---

[← 返回 Chapter 08：期末專案與架構總覽](08-final-project.md) ｜ [← 返回目錄](README.md)
