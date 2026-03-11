# CSV × JSON 指導手冊 v1.0

> **讀者定位：** 剛接觸資料交換格式的人（PM、資料分析、工程新手），或需要把資料在「Excel ↔ API ↔ DB ↔ 程式」之間搬運的人
>
> **教學目標：** 看得懂、寫得出、能除錯、能轉換、能制定團隊規範

---

## 目錄

1. [你其實每天都在用：資料交換的兩大派系](#第-1-章表格派-vs-樹狀派先選對武器)
2. [CSV：看起來很簡單，坑卻很多](#第-2-章csv-的-7-個大坑你一定會踩)
3. [JSON：更像資料「物件」，但也會讓你迷路](#第-3-章json-的-6-個迷路點巢狀會讓你頭暈)
4. [「型別」才是王](#第-4-章型別才是王你資料會壞多半不是格式是型別)
5. [轉換思維：CSV ↔ JSON 的 6 種常見形狀](#第-5-章csv--json-轉換的-6-種常見形狀)
6. [實戰：API ↔ Excel 之間搬資料](#第-6-章實戰你會真的遇到的)
7. [品質與治理：Schema、欄位字典、版本](#第-7-章品質與治理讓資料不再靠感覺)
8. [Debug 手冊：看到怪現象就照表操課](#第-8-章debug-手冊)
9. [JSON Schema × AI 理解：進階建模思維](#第-9-章json-schema--ai-理解進階建模思維)
10. [團隊規範範本：可直接貼進 README](#第-10-章團隊規範範本)
11. [練習題與解答](#練習題與解答)
12. [快速小抄 Cheat Sheet](#快速小抄-cheat-sheet)

每章都有：
- 🎭 **腦內小劇場**（你會遇到的真實情境）
- ❌ **先犯錯再救回來**（Head First 典型手法）
- ✅ **建議做法**
- 📝 **練習題**（含解答）
- 📋 **小抄**（Cheat Sheet）

---

## 第 1 章：表格派 vs 樹狀派（先選對武器）

### 🎭 腦內小劇場

> 你的同事把一份「用戶購買紀錄」用 Excel 寄給你。
> 你的工程師說他需要 JSON 格式才能進 API。
> 你的老闆說「能不能直接匯進資料庫？」
>
> 這三個人要的，其實可能是同一份資料。但格式不一樣，做法也完全不同。

### 兩大陣營一眼看懂

| 特性 | CSV（表格派） | JSON（樹狀派） |
|------|--------------|----------------|
| 外觀 | 像 Excel | 像程式碼 |
| 結構 | 扁平、每列同欄 | 可巢狀、可選欄位 |
| 人類可讀性 | 非常高 | 中等 |
| 巢狀支援 | ❌ 不支援 | ✅ 原生支援 |
| 常見用途 | 報表、批次匯入、分析 | API、設定檔、資料交換 |
| 工具支援 | Excel、Sheets、pandas | 所有現代程式語言 |

### 你在什麼時候選 CSV？

- 你要給**人類看**（Excel / Google Sheets）
- 你要做「列」為單位的**批次匯入**（大量資料）
- 你的資料是**扁平的**：每列相同欄位
- 你需要讓非工程師也能直接編輯

> 💡 **一句話：CSV 是「表格」。**

### 你在什麼時候選 JSON？

- 你在做 **API**（前後端交換資料）
- 你的資料有**巢狀結構**（一筆訂單裡有多個商品）
- 你希望欄位可以**彈性擴充**（可選欄位）
- 你需要保留型別資訊（數字、布林、null）

> 💡 **一句話：JSON 是「物件 + 清單」。**

### ❌ 常見第一個錯誤

```
我都用 CSV，比較簡單。
```

然後你遇到：「這個訂單有 3 個商品、有時有 5 個、有時有 10 個」。

CSV 的欄位是固定的，無法表達「數量不定的清單」。

✅ 正確思維：**資料有巢狀 → 選 JSON；資料扁平 → 選 CSV**。

---

## 第 2 章：CSV 的 7 個大坑（你一定會踩）

> 你以為 CSV = 用逗號分開。
> 但 CSV 真正的敵人是：**逗號、引號、換行、編碼、地區格式**。

### 坑 1：逗號不是唯一分隔符

有些系統用 `;`（歐洲 Excel 預設）、`\t`（TSV）、`|`。

```
# 逗號分隔（最常見）
name,age,city

# 分號分隔（歐洲 Excel）
name;age;city

# Tab 分隔（TSV）
name	age	city
```

✅ 建議：在規格文件中寫死 delimiter，例如：`delimiter=","`

---

### 坑 2：欄位值裡面也可能有逗號

**例：** 地址欄位 `Taipei, Taiwan`

```
# ❌ 錯誤：地址沒加引號，CSV 解析器會以為有 4 個欄位
name,address,age
Alice,Taipei, Taiwan,25

# ✅ 正確：用雙引號包住含逗號的欄位
name,address,age
Alice,"Taipei, Taiwan",25
```

**規則：只要欄位值含 delimiter，就必須用雙引號包起來。**

---

### 坑 3：欄位值裡面也可能有換行

備註欄常見：一個欄位有多行。

```
# ✅ 正確：換行也要用雙引號包起來
id,note
001,"第一行
第二行"
```

**規則：欄位裡有換行 → 也要整個用雙引號包起來。**

---

### 坑 4：雙引號本尊怎麼辦？

CSV 內如果要表示 `"`，做法是**用 `""` 雙倍表示**（RFC 4180 標準）。

```
# 原始值：He said "OK"
# CSV 寫法：
"He said ""OK"""
```

---

### 坑 5：第一列到底是不是 header？

```
# 有 header（最常見）
id,name,price
001,Alice,399

# 沒 header（第一列就是資料）
001,Alice,399
```

✅ 建議：規格中固定 `hasHeader=true/false`，程式讀取時明確指定。

---

### 坑 6：UTF-8 亂碼與 BOM

Excel 對 UTF-8 的處理很微妙，有時需要 UTF-8 with BOM 才不亂碼。

```
UTF-8 with BOM：檔案開頭有 EF BB BF 三個 byte
UTF-8 無 BOM：最乾淨，程式讀取推薦
```

✅ 建議：
- 對「要給 Excel 開」的 CSV → **UTF-8 with BOM**
- 對「給程式讀」的 CSV → **UTF-8（無 BOM）**

---

### 坑 7：空值到底是空字串還是 null？

CSV 沒有原生 null，只有「空欄位」。

```
# 這個 age 欄位是空字串？還是 null？
name,age,city
Alice,,Taipei
```

✅ 建議：契約先講清楚
- 空欄位代表 `null`（未知/未填）
- 還是代表 `""`（空字串）

這兩個在程式中是完全不同的東西。

---

### 📋 CSV 坑位小抄

| 坑 | 症狀 | 規則 |
|----|------|------|
| 分隔符 | 被分成太多欄 | 寫死 delimiter |
| 逗號在值裡 | 欄位數不對 | 加雙引號 |
| 換行在值裡 | 行數不對 | 加雙引號 |
| 雙引號在值裡 | 解析錯誤 | 用 `""` 雙倍 |
| header 問題 | 第一列被當資料 | 明確宣告 hasHeader |
| 編碼 | Excel 亂碼 | UTF-8 with BOM |
| 空值 | null vs 空字串混淆 | 契約定義清楚 |

---

## 第 3 章：JSON 的 6 個迷路點（巢狀會讓你頭暈）

### JSON 的基本型別只有這幾種

```json
{
  "name": "Alice",           // string（字串）
  "age": 25,                 // number（數字）
  "isActive": true,          // boolean（布林）
  "nickname": null,          // null（空值）
  "scores": [90, 85, 92],    // array（陣列）
  "address": {               // object（物件）
    "city": "Taipei",
    "zip": "100"
  }
}
```

> ⚠️ **重要：JSON 沒有 Date 型別、沒有 integer 型別（只有 number）。**

---

### 迷路點 1：日期其實不是日期

JSON 本身沒有 Date。日期通常是字串，但有很多種寫法：

```json
// ❌ 各種不統一的寫法（常見問題）
{ "date": "3/3/26" }
{ "date": "03-03-2026" }
{ "date": "2026年3月3日" }

// ✅ 建議：ISO 8601 格式
{ "date": "2026-03-03" }
{ "datetime": "2026-03-03T10:30:00+08:00" }
```

✅ 建議：**全團隊統一用 ISO 8601，並在 Schema 中明確宣告 `"format": "date"`**

---

### 迷路點 2：同一欄位型別飄移

```json
// ❌ 型別不穩定（你會在真實資料中遇到）
{ "userId": 123 }    // 某些資料是 number
{ "userId": "123" }  // 某些資料是 string
{ "userId": "U123" } // 某些資料還有前綴
```

✅ 建議：
- **id / 電話 / 郵遞區號**：一律用 **string**
- **金額 / 數量 / 分數**：才用 **number**
- 型別在 Schema 裡鎖死

---

### 迷路點 3：巢狀清單（最常見的設計）

```json
{
  "orderId": "A001",
  "items": [
    { "sku": "P01", "qty": 2, "price": 100 },
    { "sku": "P99", "qty": 1, "price": 399 }
  ]
}
```

這種資料要轉 CSV 時，你就得先決定：
- 「一列是訂單？」（items 資訊怎麼塞進去？）
- 「一列是品項？」（orderId 重複出現幾次？）

**這是 JSON ↔ CSV 轉換最常見的設計決策。**

---

### 迷路點 4：null vs 欄位不存在

```json
// null：欄位存在，但值是「未知/未填」
{ "nickname": null }

// 欄位不存在：這個概念根本不適用這筆資料
{ "name": "Alice" }   // 沒有 nickname 這個 key
```

這兩個語意完全不同，但很多系統把它們混用。

✅ 建議：在 Schema 裡定義：
- `nullable: true` → 允許 null
- `required: false` → 欄位可以不存在

---

### 迷路點 5：數字精度問題

```json
// JavaScript 的 number 是浮點數
// 這個值在 JS 裡可能失真：
{ "id": 9999999999999999 }

// 安全做法：超大整數 / 財務金額 → 用 string
{ "id": "9999999999999999" }
{ "amount": "399.00" }
```

---

### 迷路點 6：陣列裡的型別混用

```json
// ❌ 陣列裡型別不一致（雖然 JSON 語法允許，但很危險）
{ "scores": [90, "N/A", null, 85] }

// ✅ 同一個陣列裡應該只有同一種型別
{ "scores": [90, null, 85] }  // null 表示缺考
```

---

### 📋 JSON 型別小抄

| 欄位類型 | 建議 JSON 型別 | 注意事項 |
|----------|---------------|----------|
| ID | string | 避免 number，防止溢位 |
| 電話 | string | 含格式符號 |
| 郵遞區號 | string | 前導零不能遺失 |
| 金額 | number | 統一小數位數 |
| 數量 | number（integer）| 不應有小數 |
| 日期 | string（ISO 8601）| 明確時區 |
| 布林值 | boolean | 不要用 0/1 或 "Y"/"N" |
| 缺值 | null | 語意需定義清楚 |

---

## 第 4 章：型別才是王（你資料會壞，多半不是格式，是型別）

### 🎭 腦內小劇場

> 你把一份銷售資料匯進分析工具，想算每月總銷售額。
> 結果 `sum()` 出來是 0。
>
> 為什麼？
>
> 因為金額欄位是 `"$399"`、`"NT399"`、`"399元"` 混在一起。
> 分析工具看到的全是字串，無法加總。

### 最常壞的 5 種欄位

#### 1. ID 欄位（看似數字，但不能當數字）

```
❌ 錯誤思維：ID 都是數字，存 number 就好
✅ 正確做法：ID 一律存 string

原因：
- ID 可能有前導零（001, 002）
- ID 可能換格式（A001, B002）
- ID 不做數學運算，不需要 number 型別
```

#### 2. 金額欄位（含貨幣符號、千分位）

```
❌ 常見問題：
"$399"     → 無法直接計算
"1,299"    → 逗號被誤判為分隔符（CSV 中）
"399元"    → 含中文字

✅ 正確做法：
- 儲存時永遠用純數字：399 或 1299
- 貨幣另用獨立欄位：{ "amount": 399, "currency": "TWD" }
```

#### 3. 日期時間（時區是主要殺手）

```
❌ 常見問題：
"3/3"         → 哪一年？
"03/03/26"    → 月/日/年？還是日/月/年？
"2026-03-03"  → 幾點？哪個時區？

✅ 正確做法（ISO 8601）：
日期：  "2026-03-03"
時間：  "10:30:00"
含時區："2026-03-03T10:30:00+08:00"
UTC：  "2026-03-03T02:30:00Z"
```

#### 4. 缺值（空字串 vs null 的哲學問題）

```python
# 這三個東西在程式裡完全不同：
""      # 空字串：有值，但是空的
None    # null：沒有值
0       # 零：有值，就是零

# 範例：體重欄位
""    → 沒填（使用者跳過）
None  → 未知（系統無紀錄）
0     → 真的是零公斤（不合理）
```

#### 5. 分類欄位（大小寫、空白、同義詞）

```
❌ 同一個「台北」可能有很多種寫法：
"Taipei"
"taipei"
"TAIPEI"
" Taipei"   ← 前面有空格
"台北"
"台北市"

✅ 正確做法：
- 建立 enum（允許值清單）
- 資料進入時做正規化
- Schema 中用 "enum": ["Taipei", "Kaohsiung", ...] 鎖定
```

### ✅ 資料傳輸「保守策略」小抄

```
1. 能用 string 表示，就先用 string
   → 型別轉換在「需要運算的時候」才做

2. 日期用 ISO 8601 字串
   → 時區規則另外文件化

3. null 的語意要定義
   → 未知？不存在？未填？三種不同的 null

4. 金額不含符號
   → 符號另用 currency 欄位表達

5. 分類欄位建 enum
   → 讓 Schema 幫你擋掉亂填的值
```

---

## 第 5 章：CSV ↔ JSON 轉換的 6 種常見形狀

### 形狀 1：Row Object（最常見）

每列 CSV 對應一個 JSON object。

```
CSV：
id,name,age
001,Alice,25
002,Bob,30

JSON：
[
  { "id": "001", "name": "Alice", "age": 25 },
  { "id": "002", "name": "Bob", "age": 30 }
]
```

---

### 形狀 2：Array of Rows（整份資料）

整份 CSV 對應一個 JSON array。這其實就是形狀 1 的外層包裝。

```json
{
  "data": [
    { "id": "001", "name": "Alice" },
    { "id": "002", "name": "Bob" }
  ],
  "total": 2,
  "page": 1
}
```

---

### 形狀 3：Nested List（一對多，地獄模式）

一筆主資料對應多筆子資料。

```
CSV（一列是品項）：
orderId,sku,qty
A001,P01,2
A001,P99,1
A002,P01,5

JSON（一筆是訂單）：
[
  {
    "orderId": "A001",
    "items": [
      { "sku": "P01", "qty": 2 },
      { "sku": "P99", "qty": 1 }
    ]
  },
  {
    "orderId": "A002",
    "items": [
      { "sku": "P01", "qty": 5 }
    ]
  }
]
```

> ⚠️ 這個轉換需要先「GROUP BY orderId」再組合。

---

### 形狀 4：Key-Value Map

兩欄 CSV 對應 JSON object。

```
CSV：
key,value
color,blue
size,large
weight,1.5

JSON：
{
  "color": "blue",
  "size": "large",
  "weight": 1.5
}
```

---

### 形狀 5：Wide ↔ Long（分析資料最常用）

**Wide（寬表）**：每個指標一個欄位

```
date,taipei,kaohsiung,taichung
2026-01-01,100,80,90
2026-01-02,105,82,88
```

**Long（長表）**：每列一個觀測值

```
date,city,value
2026-01-01,taipei,100
2026-01-01,kaohsiung,80
2026-01-01,taichung,90
2026-01-02,taipei,105
```

> 📊 分析工具（pandas、R）通常偏好 Long 表格式。

---

### 形狀 6：JSON Lines / NDJSON（大數據、串流）

每行一個完整的 JSON object，沒有外層陣列。

```jsonl
{"id": "001", "name": "Alice", "age": 25}
{"id": "002", "name": "Bob", "age": 30}
{"id": "003", "name": "Carol", "age": 28}
```

> 💡 優點：可以逐行讀取，不需要把整個檔案載入記憶體。適合大型資料集。

---

## 第 6 章：實戰（你會真的遇到的）

### 情境 A：API 回 JSON，你要給同事 Excel 看

```
API 回傳 JSON
    ↓
1. 把 JSON 正規化成「一列一物件」
   （巢狀結構需要先展開或拆成多個 sheet）
    ↓
2. 欄位順序固定（避免每次順序不同）
    ↓
3. 匯出 CSV（必要時加 UTF-8 with BOM）
    ↓
4. 給同事開啟驗證
```

**Python 範例（pandas）：**

```python
import json
import pandas as pd

# 讀取 JSON
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 轉換成 DataFrame（假設是 flat 結構）
df = pd.DataFrame(data)

# 匯出 CSV（加 BOM 讓 Excel 不亂碼）
df.to_csv("output.csv", index=False, encoding="utf-8-sig")
```

---

### 情境 B：同事給你 CSV，你要餵進 API

```
同事給你 CSV
    ↓
1. 欄位驗證（必填欄位是否都有？型別是否正確？）
    ↓
2. 空值規則套用（空欄位 → null？還是預設值？）
    ↓
3. 型別轉換（字串 "25" → 數字 25）
    ↓
4. 轉成 JSON array
    ↓
5. 送 API
```

**Python 範例：**

```python
import csv
import json

records = []
with open("data.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # 空值處理
        record = {
            k: (None if v == "" else v)
            for k, v in row.items()
        }
        # 型別轉換
        if record.get("age"):
            record["age"] = int(record["age"])
        records.append(record)

print(json.dumps(records, ensure_ascii=False, indent=2))
```

---

### 情境 C：Python 解析 JSON（基本功）

```python
import json

# 讀取 JSON 字串
json_str = '{"name": "Alice", "age": 25, "city": "Taipei"}'
data = json.loads(json_str)
print(data["name"])   # 輸出：Alice
print(data["age"])    # 輸出：25（是 int，不是字串）

# 讀取 JSON 檔案
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 寫入 JSON 檔案
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

---

### 情境 D：Python 解析 CSV（基本功）

```python
import csv

# 讀取 CSV（DictReader 讓每列變成 dict）
with open("data.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row["name"], row["age"])

# 寫入 CSV
fieldnames = ["id", "name", "age"]
with open("output.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow({"id": "001", "name": "Alice", "age": 25})
```

---

## 第 7 章：品質與治理（讓資料不再「靠感覺」）

### 你需要三樣東西

#### 1) 欄位字典（Data Dictionary）

讓所有人對「這個欄位是什麼」有共識。

| 欄位名 | 型別 | 必填 | 範例值 | 說明 |
|--------|------|------|--------|------|
| userId | string | ✅ | "U-00123" | 用戶唯一識別碼，格式：U-{5位數字} |
| purchaseAmount | number | ✅ | 399.0 | 購買金額，單位依 currency |
| currency | string | ❌ | "TWD" | 貨幣，預設 TWD |
| purchaseDate | string | ✅ | "2026-03-03" | ISO 8601 日期格式 |

---

#### 2) JSON Schema（讓機器幫你驗資料）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["userId", "purchaseAmount", "purchaseDate"],
  "properties": {
    "userId": {
      "type": "string",
      "pattern": "^U-[0-9]{5}$"
    },
    "purchaseAmount": {
      "type": "number",
      "minimum": 0
    },
    "currency": {
      "type": "string",
      "enum": ["TWD", "USD", "JPY"]
    },
    "purchaseDate": {
      "type": "string",
      "format": "date"
    }
  },
  "additionalProperties": false
}
```

這段 Schema 的效果：
- 型別錯 → 直接擋掉
- 缺必填欄位 → 擋掉
- 負數金額 → 擋掉
- 不在 enum 裡的貨幣 → 擋掉
- 多出不明欄位 → 擋掉

---

#### 3) 版本（Versioning）

```json
// v1 的資料
{ "schemaVersion": "v1", "userId": "001", "amount": 399 }

// v2 新增欄位（向後相容，OK）
{ "schemaVersion": "v2", "userId": "001", "amount": 399, "currency": "TWD" }

// 改名 amount → purchaseAmount（不相容！需要版本升級）
{ "schemaVersion": "v3", "userId": "001", "purchaseAmount": 399, "currency": "TWD" }
```

**版本升級規則：**
- ✅ 新增可選欄位 → 通常向後相容
- ✅ 放寬型別限制 → 通常向後相容
- ❌ 改欄位名稱 → **不相容，需升版本**
- ❌ 改型別（string → number）→ **不相容，需升版本**
- ❌ 移除欄位 → **不相容，需升版本**

---

## 第 8 章：Debug 手冊

> 看到怪現象，照表操課，不要猜。

### CSV Debug 表

| 症狀 | 最可能原因 | 第一招 |
|------|-----------|--------|
| Excel 開起來亂碼 | 編碼/BOM 問題 | 改存 UTF-8 with BOM |
| 行數變少 | 欄位內含換行但沒用引號包覆 | 檢查雙引號包覆是否正確 |
| 某列欄位數暴增 | 欄位值含 delimiter 但沒加引號 | 搜尋那列是否含逗號 |
| 數字前導零消失 | Excel 自動轉型別 | 匯入時設定該欄為「文字」格式 |
| 日期格式亂掉 | Excel 自動推斷日期格式 | 匯入時明確指定日期欄位格式 |
| 最後一列被吃掉 | 換行符號問題（\n vs \r\n）| 統一換行符 |

### JSON Debug 表

| 症狀 | 最可能原因 | 第一招 |
|------|-----------|--------|
| JSON 解析失敗 | 多了/少了逗號，或引號錯 | 貼進 JSON linter（jsonlint.com）|
| 數字變成科學記號 | 太大的整數被 float 處理 | 改用 string 型別 |
| null 與 undefined 混亂 | JS 特有問題 | JSON.stringify 前先處理 undefined |
| 中文亂碼 | ensure_ascii 沒關掉 | `json.dump(..., ensure_ascii=False)` |
| 巢狀取值失敗 | key 不存在或是 None | 先檢查 key 是否存在，用 `.get()` |

### 🛠️ 常用工具

| 工具 | 用途 |
|------|------|
| `jsonlint.com` | JSON 語法檢查 |
| `csvlint.io` | CSV 格式驗證 |
| Python `json.tool` | 命令列格式化 JSON |
| VS Code + 擴充套件 | JSON/CSV 語法高亮 + 驗證 |
| `pandas` | DataFrame 轉換，查型別問題 |

---

## 第 9 章：JSON Schema × AI 理解（進階建模思維）

> 這一章不只是講格式。
> 這一章講的是：**你的資料長什麼樣子，AI 就會怎麼理解你。**

### 🎭 腦內小劇場：兩份資料，AI 看到的差異

**版本 A（模糊）：**

```json
{
  "user": "Aaron",
  "data": "399",
  "time": "3/3"
}
```

**版本 B（清晰）：**

```json
{
  "userId": "U-00123",
  "purchaseAmount": 399.0,
  "currency": "TWD",
  "purchaseDate": "2026-03-03"
}
```

哪一份資料比較容易讓分析工具理解？讓 SQL 查詢清楚？讓 AI 正確推論？讓未來系統升級？

**答案永遠是 B。**

原因不是漂亮，原因是：**結構清晰 = 語意明確 = 可推理性提升。**

---

### AI 是怎麼「讀」你的 JSON？

很多人以為 AI 只看值。其實 AI 同時看：

- **欄位名稱** → 推斷語意
- **結構層級** → 推斷關係
- **陣列 vs 物件** → 推斷「集合」還是「單一實體」
- **型別** → 推斷可以做什麼操作
- **是否巢狀** → 推斷語意群組

---

### 欄位命名如何影響 AI 理解

```json
// ❌ 模糊命名 → AI 幾乎無法推理
{
  "a": 399,
  "b": "2026-03-03"
}

// ✅ 語意清楚命名 → AI 能自動建立「交易事件」語意
{
  "purchaseAmount": 399,
  "purchaseDate": "2026-03-03"
}
```

**命名原則：**
1. 使用完整單字（不要縮寫：`amt`、`dt`、`cnt`）
2. 使用語意導向名稱（`purchaseAmount` 比 `amount` 更好）
3. 保持一致（不要 `amount` / `totalAmount` 混用）
4. camelCase 或 snake_case 選一個，全專案統一

---

### 巢狀結構會改變資料意義

```json
// ❌ 扁平錯誤設計（無法擴充，AI 會困惑）
{
  "orderId": "A01",
  "sku1": "P01",
  "qty1": 2,
  "sku2": "P99",
  "qty2": 1
}

// ✅ 正確巢狀（AI 可以理解「訂單包含多個商品」）
{
  "orderId": "A01",
  "items": [
    { "sku": "P01", "qty": 2 },
    { "sku": "P99", "qty": 1 }
  ]
}
```

**巢狀 = 語意群組。用結構來表達「這些欄位屬於同一個概念」。**

---

### Schema × 分析 × AI 的核心結論

```
結構 = 語意
型別 = 邏輯
命名 = 概念
巢狀 = 關係
```

**資料設計得好：**
- 分析工具可以直接運算
- ETL 前處理減少
- AI 推論穩定、準確
- 系統可擴充、技術債少

**資料設計得亂：**
- 每次分析都要先清洗
- AI 可能誤判型別、誤判語意
- 維運成本暴增
- 技術債快速累積

---

## 第 10 章：團隊規範範本

> 這些範本可以直接貼進你的 README 或 Confluence。

### CSV 格式契約

```yaml
CSV Format Contract v1.0
---
delimiter:    ","
encoding:     "UTF-8 with BOM"  # 給 Excel 使用
              "UTF-8"            # 給程式使用
hasHeader:    true
quoting:      RFC4180  # 用 " 包覆含特殊字元的欄位
newline:      "\n"     # 或明確寫 CRLF
null_policy:  空欄位 = null（不是空字串）
date_format:  ISO 8601 (YYYY-MM-DD)
required_columns: [id, name, createdAt]
column_order: fixed   # 欄位順序不能任意調換
```

### JSON 格式契約

```yaml
JSON Format Contract v1.0
---
encoding:         UTF-8
date_format:      ISO 8601 ("2026-03-03")
datetime_format:  ISO 8601 with timezone ("2026-03-03T10:30:00+08:00")
id_type:          string（永遠用 string，不用 number）
null_semantics:
  null:           欄位存在，值未知/未填
  key_absent:     概念不適用此筆資料
naming_convention: camelCase
schema_version:   在每份資料或 API response 中標註
additionalProperties: false  # 不允許 Schema 以外的欄位
```

---

## 練習題與解答

### 第 2 章練習

**練習 2-1：CSV 引號逃脫**

把這三個值正確寫成一列 CSV 欄位：

1. `Taipei, Taiwan`
2. `He said "OK"`
3. 兩行文字（第一行：Hello，第二行：World）

**解答：**

```
"Taipei, Taiwan","He said ""OK""","Hello
World"
```

---

**練習 2-2：判斷這個 CSV 哪裡有問題**

```
name,address,note
Alice,Taipei, Taiwan,一般用戶
Bob,"Kaohsiung",VIP,"高消費用戶"
```

> 第 2 列：`Taipei, Taiwan` 沒有引號包覆，CSV 解析器會以為有 4 個欄位。
> 解法：改為 `"Taipei, Taiwan"`

---

### 第 3 章練習

**練習 3-1：JSON 型別判斷**

下面哪些是「number」哪些該用「string」？

| 值 | 你的判斷 |
|----|--------|
| `00123`（訂單號碼）| ? |
| `0912345678`（電話）| ? |
| `399.0`（商品金額）| ? |
| `100`（庫存數量）| ? |

**解答：**
- `00123` → **string**（前導零會遺失）
- `0912345678` → **string**（電話不做運算）
- `399.0` → **number**（需要加總）
- `100` → **number**（需要計算）

---

**練習 3-2：修正這份 JSON**

```json
{
  "id": 123,
  "phone": 912345678,
  "amount": "$399",
  "date": "3/3/26",
  "status": "1"
}
```

**修正後：**

```json
{
  "id": "123",
  "phone": "0912345678",
  "amount": 399.0,
  "currency": "TWD",
  "date": "2026-03-03",
  "status": true
}
```

---

### 第 5 章練習

**練習 5-1：巢狀轉扁平**

把下面的 JSON 轉成 CSV（一列一品項）：

```json
[
  {
    "orderId": "A001",
    "customer": "Alice",
    "items": [
      { "sku": "P01", "qty": 2 },
      { "sku": "P99", "qty": 1 }
    ]
  }
]
```

**解答：**

```
orderId,customer,sku,qty
A001,Alice,P01,2
A001,Alice,P99,1
```

---

## 快速小抄 Cheat Sheet

### CSV 必知規則

```
1. 欄位值含分隔符 → 加雙引號包覆
2. 欄位值含換行   → 加雙引號包覆
3. 欄位值含雙引號 → 用 "" 雙倍表示
4. 給 Excel 用   → UTF-8 with BOM
5. 給程式用       → UTF-8（無 BOM）
6. 空欄位 ≠ null  → 需在契約中定義
```

### JSON 必知規則

```
1. 沒有 Date 型別  → 用 ISO 8601 字串
2. ID/電話/郵遞區號 → 永遠用 string
3. 金額/數量       → 用 number
4. 布林值          → true/false，不要 "Y"/"N" 或 1/0
5. null            → 欄位存在但值未知
6. 欄位不存在      → 概念不適用此筆資料
```

### Python 常用片段

```python
# 讀 JSON
import json
data = json.loads(json_str)
data = json.load(open("file.json", encoding="utf-8"))

# 寫 JSON（中文不跳脫，縮排 2）
json.dumps(data, ensure_ascii=False, indent=2)

# 讀 CSV（自動 header）
import csv
reader = csv.DictReader(open("file.csv", encoding="utf-8"))
for row in reader:
    print(row["name"])

# 寫 CSV（Excel 友善）
writer = csv.DictWriter(
    open("out.csv", "w", encoding="utf-8-sig"),
    fieldnames=["id", "name"]
)
writer.writeheader()
writer.writerow({"id": "001", "name": "Alice"})

# CSV ↔ JSON（用 pandas）
import pandas as pd
df = pd.read_csv("data.csv")
df.to_json("data.json", orient="records", force_ascii=False)
```

### 快速決策樹

```
資料要給人類用 Excel 看？
  → CSV

資料要做 API 傳輸？
  → JSON

資料有一對多結構（訂單含商品）？
  → JSON（巢狀）或 CSV（展開成多列）

資料需要機器驗證？
  → 加上 JSON Schema

資料要大量串流處理？
  → JSON Lines (NDJSON)
```

---

*CSV × JSON 指導手冊（Head First 版）v1.0*
*涵蓋簡報：資料科學課程 JSON 和 CSV 格式介紹與資料解析*
*Author: Aaron | 2026-03-03*