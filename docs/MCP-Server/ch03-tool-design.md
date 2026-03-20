# 第三章：工具設計的藝術

## ──為什麼 Claude 就是不呼叫你的工具？

---

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  小明的 MCP Server：                                        │
│  工具：search_knowledge_base                                │
│  使用者問：「我們的退換貨政策是什麼？」                     │
│  結果：Claude 直接回答，根本沒呼叫工具 😭                  │
│                                                             │
│  小華的 MCP Server：                                        │
│  工具：search_knowledge_base（完全一樣的程式碼！）          │
│  使用者問：「我們的退換貨政策是什麼？」                     │
│  結果：Claude 立刻呼叫工具，搜尋，回傳正確答案 ✅           │
│                                                             │
│  差別是什麼？                                               │
│  小明的 description：「搜尋資料」                           │
│  小華的 description：[你等一下就會看到]                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

在工具設計研討會上，老師問了一個問題：

「你們有沒有遇到過 Claude 在應該呼叫工具的時候，卻直接回答——給了一個錯的答案？」

全班 30 個人，有 28 個人舉手。

然後老師問：「那你們有沒有認真讀過自己工具的 description，想想 Claude 看到這個描述會怎麼想？」

只有 3 個人舉手。

這就是問題所在。

---

## 3.1 Description 工程：你和 AI 的合約

**描述（description）** 不只是說明文件。對 AI 來說，description 是一份**合約**——它規定了：

- **何時**應該呼叫這個工具（觸發條件）
- **何時**不應該呼叫（排除條件）
- **如何**使用參數（使用說明）
- **期望**得到什麼樣的回傳（預期輸出）

AI 不會讀程式碼，它只能看 description。你的工具再厲害，description 寫得爛，AI 就是不知道要用它。

### 三個版本的描述，三種結果

讓我們看同一個工具的三個版本：

```python
# ❌ 壞版本：AI 完全不知道何時要用
@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """搜尋資料"""
    # ...實作...
```

問題：「搜尋」什麼資料？什麼情況下要搜尋？這個工具有什麼和「直接回答」不同的地方？

```python
# ⚠️  普通版本：AI 有時候會用，有時候不確定
@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """在知識庫中搜尋相關內容"""
    # ...實作...
```

好一點，但還是不夠。AI 仍然不知道知識庫裡有什麼，不知道什麼時候「需要搜尋」而不是「直接回答」。

```python
# ✅ 好版本：AI 知道何時該用、不該用
@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """
    搜尋公司的產品知識庫，取得關於產品規格、退換貨政策、FAQ 和使用說明的資訊。

    【何時呼叫此工具】
    - 使用者詢問產品功能、規格或使用方法
    - 使用者詢問退換貨政策、保固條款
    - 使用者提出 FAQ 類型的問題（「如何...」「可以嗎...」「為什麼...」）
    - 任何需要查閱官方文件才能準確回答的問題

    【何時不要呼叫此工具】
    - 使用者只是閒聊或說謝謝
    - 問的是通識問題（天氣、時間、一般常識）
    - 已經搜尋過相同查詢，且結果仍在對話上下文中

    query 是搜尋關鍵詞，用使用者問題的核心詞彙即可。
    top_k 是最多回傳幾筆結果，預設 5 筆，一般情況不需要修改。
    """
    # ...實作...
```

> **重要**：好的 description 通常比程式碼本體還長。這是正常的。**Description 是給 AI 看的，程式碼是給電腦執行的。**
>
> 這讓很多工程師不太舒服——我們習慣用程式碼說話，不習慣用文字。但你必須轉換思維：在 MCP 的世界裡，description 是工具的**第一公民**。

---

### 腦力激盪 🧠

> 如果 Claude 在應該呼叫工具的情況下卻直接回答，你應該改哪裡？
> 如果 Claude 在不應該呼叫工具的情況下卻呼叫了，你又應該改哪裡？

<details>
<summary>點開看答案</summary>

**Claude 不呼叫工具（但應該要）：**

通常是 description 沒有清楚說明**何時**應該呼叫這個工具。AI 不知道這個工具比「直接回答」更好。解法：在 description 裡加「何時呼叫」的觸發條件。

**Claude 亂呼叫工具（不應該時卻呼叫）：**

通常是 description 太模糊，或沒有說明**排除條件**。解法：在 description 裡加「何時不要呼叫」的說明，讓 AI 知道邊界。

</details>

---

## 3.2 五個設計陷阱

這五個陷阱是真實 MCP 開發中最常見的問題，每一個都可能讓你的工具從「可用」變成「廢物」。

---

### 陷阱一：Description 太模糊

**症狀**：Claude 有時呼叫工具，有時直接回答，行為不一致。

```python
# ❌ 有問題的版本
@mcp.tool()
def get_info(topic: str) -> str:
    """取得資訊"""
    ...
```

**修復**：說清楚是什麼資訊、從哪裡來、什麼時候要用：

```python
# ✅ 修復後
@mcp.tool()
def get_product_info(product_id: str) -> str:
    """
    從產品資料庫取得特定產品的詳細資訊，包括規格、庫存狀態和定價。

    當使用者詢問特定產品的詳細資料時呼叫此工具。
    product_id 是產品的唯一識別碼，格式為 "PROD-XXXX"（例如 PROD-1234）。
    """
    ...
```

---

### 陷阱二：工具數量超過 7 個

**症狀**：Claude 呼叫錯誤的工具，或在有更適合的工具時選了次要的工具。

```
研究發現：
當可用工具數量從 5 增加到 10，
AI 模型的工具選擇準確率會下降約 15-25%。

這是因為語言模型的注意力機制有限，
工具太多時，模型在做選擇時的「決策空間」過大。
```

**修復**：

1. **檢視是否有重複功能**的工具，合併它們
2. **按照使用場景**分拆成多個 MCP Server（每個 Server 負責一個領域）
3. **把低頻工具**做成 Resource 或 Prompt，而不是 Tool

```
範例：從 12 個工具整理為 2 個 MCP Server

整理前：                     整理後：
─────────────────────────    ─────────────────────────────────
1. search_products           MCP Server A（產品服務，≤5工具）：
2. get_product_detail          • search_products
3. list_categories             • get_product_detail
4. get_inventory               • list_categories
5. create_order                • check_inventory_and_order
6. cancel_order
7. get_order_status          MCP Server B（訂單服務，≤4工具）：
8. list_orders                 • create_order
9. search_customers            • cancel_order
10. get_customer_info          • get_order_status
11. update_customer            • list_customer_orders
12. list_customer_orders
```

> **提醒**：「≤7 個工具」是一個經驗法則，不是鐵律。實際上，如果你的工具 description 都寫得非常清晰、互相之間沒有歧義，超過 7 個也可能運作得不錯。但這個原則是個好的起點。

---

### 陷阱三：參數命名不一致

**症狀**：Claude 在呼叫工具時傳錯參數，或把不同工具的參數搞混。

```python
# ❌ 有問題的版本：同樣的概念，三種命名方式
@mcp.tool()
def get_user(user_id: int) -> str: ...

@mcp.tool()
def update_user(userId: str) -> str: ...  # 駝峰式！字串型別！

@mcp.tool()
def delete_user(uid: int) -> str: ...   # 縮寫！
```

AI 看到三個不同的參數名稱，可能把 `user_id`、`userId`、`uid` 當成不同的東西。

**修復**：建立並嚴格遵守命名規範：

```python
# ✅ 修復後：一致的命名
# 規則：snake_case，完整詞彙，不縮寫

@mcp.tool()
def get_user(user_id: int) -> str:
    """取得指定用戶的詳細資訊。user_id 是整數型的用戶唯一識別碼。"""
    ...

@mcp.tool()
def update_user(user_id: int, display_name: str) -> str:
    """更新用戶的顯示名稱。user_id 與 get_user 的 user_id 相同。"""
    ...

@mcp.tool()
def delete_user(user_id: int) -> str:
    """刪除指定用戶。user_id 與 get_user 的 user_id 相同。"""
    ...
```

在 description 裡明確說明「這個參數和 X 工具的 Y 參數是同樣的東西」，可以大幅減少 AI 的混淆。

---

### 陷阱四：錯誤訊息對 AI 沒意義

**症狀**：工具出錯，但 Claude 無法判斷問題出在哪，也無法引導使用者修正。

```python
# ❌ 有問題的版本：錯誤訊息對 AI 沒有用
@mcp.tool()
def get_user(user_id: int) -> str:
    user = db.find(user_id)
    if not user:
        return "Error 404"  # AI 看到這個能做什麼？
    return json.dumps(user)
```

Claude 看到「Error 404」，只能說「發生了一個錯誤」，無法幫助使用者。

```python
# ✅ 修復後：錯誤訊息讓 AI 能引導使用者
@mcp.tool()
def get_user(user_id: int) -> str:
    """
    取得指定用戶的資訊。user_id 是整數型的用戶唯一識別碼。
    如果找不到用戶，會回傳說明原因的錯誤訊息。
    """
    user = db.find(user_id)
    if not user:
        # 告訴 AI：是什麼找不到、為什麼找不到、用戶可以怎麼辦
        return (
            f"找不到 user_id={user_id} 的使用者。"
            "可能的原因：(1) ID 不存在，(2) 用戶已被刪除。"
            "請確認 ID 是否正確，或嘗試使用 search_users 工具搜尋用戶名稱。"
        )
    return json.dumps(user, ensure_ascii=False)
```

**一個好的錯誤訊息包含**：
1. 發生了什麼（找不到 X）
2. 可能的原因（為什麼找不到）
3. 建議的下一步（用戶或 AI 可以怎麼辦）

---

### 陷阱五：有副作用但未聲明

**症狀**：AI 不知道某個工具會產生無法復原的後果，在不適當的時機呼叫了它。

```python
# ❌ 危險版本：沒有說明副作用
@mcp.tool()
def process_request(request_id: str) -> str:
    """處理請求"""
    # 這個函式實際上會：發送通知郵件 + 更新資料庫 + 觸發付款
    # 但 description 完全沒提到！
    send_notification_email(request_id)
    update_database(request_id)
    trigger_payment(request_id)
    return f"已處理請求 {request_id}"
```

```python
# ✅ 修復後：明確說明副作用
@mcp.tool()
def process_request(request_id: str) -> str:
    """
    處理指定的請求，這是一個不可逆的操作。

    ⚠️  此工具會執行以下動作：
    1. 向請求關聯的用戶發送確認通知郵件
    2. 將請求狀態更新為「已處理」（無法復原）
    3. 觸發付款流程

    【僅在以下情況呼叫】
    - 用戶明確說「我要處理請求」或「確認執行」
    - 不要在用戶只是詢問狀態時呼叫此工具（請改用 get_request_status）

    request_id 是請求的唯一識別碼，格式為 "REQ-XXXX"。
    """
    send_notification_email(request_id)
    update_database(request_id)
    trigger_payment(request_id)
    return f"請求 {request_id} 已成功處理。確認郵件已發送，付款已觸發。"
```

> **重要**：任何會**修改資料**、**發送訊息**、**觸發付款**、**刪除內容**的工具，都必須在 description 裡明確聲明。AI 看到這些警告，才能在適當的時機才呼叫——通常是在得到使用者的明確確認之後。

---

## 3.3 錯誤回傳設計：不要讓你的工具崩潰

MCP 工具函式有一個重要的設計原則：**工具不應該 raise exception，應該回傳描述性的錯誤字串**。

為什麼？

```
raise exception 的問題：

1. MCP 協議會把 exception 轉換成一個通用的錯誤訊息
2. Claude 看到的是：「工具執行失敗」
3. Claude 不知道為什麼失敗，也不知道怎麼幫用戶

回傳錯誤字串的好處：

1. Claude 可以讀到具體的錯誤資訊
2. Claude 可以根據錯誤類型給出適當的建議
3. 使用者得到有用的回饋，而不是「發生了錯誤」
```

### 錯誤處理的完整範例

```python
# server.py — 展示完整的錯誤處理設計
from mcp.server.fastmcp import FastMCP
import json
import httpx

mcp = FastMCP("資料服務")

# 一個模擬的資料庫
USERS = {
    1: {"name": "小明", "email": "ming@example.com", "role": "admin"},
    2: {"name": "小華", "email": "hua@example.com", "role": "user"},
    3: {"name": "小美", "email": "mei@example.com", "role": "user"},
}

@mcp.tool()
def get_user(user_id: int) -> str:
    """
    取得指定用戶的詳細資訊（姓名、Email、角色）。

    當使用者詢問特定用戶的資料時呼叫此工具。
    user_id 是正整數，可用 list_users 工具取得可用的 ID 列表。
    """
    # 驗證輸入：user_id 必須是正整數
    if user_id <= 0:
        return f"錯誤：user_id 必須是正整數，但收到 {user_id}。請使用 1 或更大的整數。"

    # 查詢用戶
    user = USERS.get(user_id)
    if user is None:
        # 提供有用的錯誤訊息：告訴 AI 有哪些可用的 ID
        available_ids = list(USERS.keys())
        return (
            f"找不到 user_id={user_id} 的使用者。"
            f"目前可用的用戶 ID 為：{available_ids}。"
            "請確認 ID 是否正確。"
        )

    # 成功！回傳格式化的 JSON 字串
    return json.dumps(user, ensure_ascii=False, indent=2)


@mcp.tool()
def list_users() -> str:
    """
    列出所有用戶的 ID 和姓名。

    當需要知道有哪些用戶、或在呼叫 get_user 之前確認 ID 時使用。
    回傳一個包含所有用戶 ID 和姓名的列表。
    """
    users_summary = [
        {"user_id": uid, "name": info["name"]}
        for uid, info in USERS.items()
    ]
    return json.dumps(users_summary, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
```

### 結構化錯誤回傳的模式

```python
# 推薦的錯誤回傳模式
def 某個工具(參數: str) -> str:
    # 驗證輸入
    if not 參數:
        return "錯誤：參數不能是空字串。[說明如何正確呼叫]"

    # 執行主要邏輯
    try:
        結果 = 執行某些操作(參數)
        return json.dumps(結果, ensure_ascii=False)

    except 特定的錯誤類型 as e:
        # 轉換成對 AI 有意義的訊息
        return f"錯誤：[具體說明發生了什麼]。可能原因：[為什麼]。建議：[怎麼辦]"

    except Exception as e:
        # 最後的防線：捕獲所有未預期錯誤
        return f"錯誤：執行時發生未預期的問題：{str(e)}"
```

---

### 腦力激盪 🧠

> 為什麼工具應該回傳人類可讀的字串，而不是直接 raise exception？
> 試著從 AI 的視角思考：如果你是 Claude，你更喜歡看到什麼？

---

## 3.4 工具拆分 vs 合併：決策框架

什麼時候應該把功能放進一個工具？什麼時候應該拆成兩個？

### 決策流程圖

```
這個功能應該是一個工具還是多個工具？

                    ┌─────────────────────────┐
                    │   這兩個功能的核心任務   │
                    │   是同一件事嗎？        │
                    └────────────┬────────────┘
                          是 ↓         ↓ 否
                    ┌─────────┐    ┌──────────────────┐
                    │ 用參數  │    │ 它們的觸發條件   │
                    │ 區分    │    │ 有重疊嗎？       │
                    └─────────┘    └────────┬─────────┘
                                      有 ↓        ↓ 沒有
                                  ┌─────────┐  ┌──────────┐
                                  │ 考慮合  │  │ 拆成兩   │
                                  │ 併，但  │  │ 個獨立   │
                                  │ 要小心  │  │ 工具     │
                                  └─────────┘  └──────────┘
```

### 具體範例：搜尋工具要合還是拆？

```python
# 情境：你有兩種搜尋——關鍵字搜尋和語意搜尋

# 選項 A：合併成一個工具（參數控制）
@mcp.tool()
def search(query: str, search_type: str = "semantic") -> str:
    """
    搜尋知識庫。search_type 可以是 "semantic"（語意搜尋）或 "keyword"（關鍵字搜尋）。
    """
    if search_type == "semantic":
        return semantic_search(query)
    else:
        return keyword_search(query)

# 選項 B：拆成兩個工具
@mcp.tool()
def semantic_search(query: str) -> str:
    """
    用語意相似度搜尋知識庫。適合用自然語言描述的模糊查詢，
    例如「怎麼設定付款方式」、「遇到登入問題怎麼辦」。
    """
    ...

@mcp.tool()
def keyword_search(keywords: str) -> str:
    """
    用精確關鍵字搜尋知識庫。適合搜尋特定詞彙、產品型號、錯誤代碼，
    例如「ERR-404」、「iPhone 15 Pro」。
    """
    ...
```

**什麼時候合併（選項 A）**：
- 兩個功能的使用場景幾乎完全重疊
- 用戶（或 AI）很難決定該用哪一個
- 功能實際上很相似，只是細節不同

**什麼時候拆開（選項 B）**：
- 兩個功能的適用場景有明確差異
- 讓 AI 根據使用情境選擇更合適的工具
- 每個工具可以有更精確的 description

在這個例子裡，選項 B 更好——因為「語意搜尋」和「關鍵字搜尋」的適用場景是不同的，AI 可以根據使用者的問題類型自動選擇。

### 單一職責原則應用到 MCP Tools

借用軟體設計的 **單一職責原則（Single Responsibility Principle）**：

> 一個工具應該只做一件事，而且把它做好。

```python
# ❌ 違反單一職責
@mcp.tool()
def user_manager(action: str, user_id: int, data: str = "") -> str:
    """根據 action 參數（get/create/update/delete）管理用戶"""
    if action == "get": ...
    elif action == "create": ...
    elif action == "update": ...
    elif action == "delete": ...
    # AI 需要記住 4 個不同的 action，而且每個 action 的參數需求都不同
```

```python
# ✅ 遵守單一職責（但要注意總工具數！）
@mcp.tool()
def get_user(user_id: int) -> str:
    """取得指定用戶的資訊"""
    ...

@mcp.tool()
def create_user(name: str, email: str, role: str = "user") -> str:
    """建立新用戶"""
    ...

@mcp.tool()
def update_user_role(user_id: int, new_role: str) -> str:
    """更新用戶的角色（admin/user/guest）"""
    ...

@mcp.tool()
def delete_user(user_id: int) -> str:
    """刪除指定用戶（不可復原）"""
    ...
```

---

## 3.5 MCP Inspector 實戰：在接 Claude Desktop 之前先驗證

在把 MCP Server 連接到 Claude Desktop 之前，先用 **MCP Inspector** 徹底測試是個好習慣。Inspector 讓你能夠：

1. 看到所有工具的完整 Schema（這就是 AI 看到的）
2. 手動傳入不同的參數值，觀察輸出
3. 看到底層的 JSON-RPC 請求和回應（debug 神器）
4. 確認錯誤處理是否正常運作

```bash
# 啟動 Inspector
mcp dev server.py
```

Inspector 啟動後，打開 `http://localhost:5173`：

```
Inspector 的四個區域：

┌─────────────────────────────────────────────────┐
│  左側：工具列表                                  │
│  • 點選工具名稱                                  │
│  • 看到完整 description 和 Schema               │
│  • 確認參數型別、必填/選填設定是否正確           │
├─────────────────────────────────────────────────┤
│  中間：呼叫工具                                  │
│  • 填寫參數值（JSON 格式）                      │
│  • 按 "Call Tool" 執行                          │
│  • 測試正常情況和錯誤情況                        │
├─────────────────────────────────────────────────┤
│  右上：工具回傳結果                              │
│  • 這就是 AI 看到的文字                         │
│  • 確認格式是否清楚、有沒有亂碼                  │
├─────────────────────────────────────────────────┤
│  右下：原始 JSON-RPC 訊息                        │
│  • 看底層協議訊息                               │
│  • Debug 時很有用                               │
└─────────────────────────────────────────────────┘
```

### Inspector 的測試清單

對每個工具，測試以下情況：

```
✅ 正常情況：傳入有效的參數，確認回傳格式正確
✅ 邊界情況：傳入空字串、0、很長的字串
✅ 錯誤情況：傳入不存在的 ID、錯誤的格式
✅ 選填參數：只傳必填參數，確認選填參數的預設值正確
✅ Description 審查：在 Inspector 裡看到的 description，
                      想像自己是 AI，你看得懂嗎？
```

---

## 動手做：重構一個爛設計的 MCP Server

這個 Lab 的目標：找出問題、理解原因、修復它。

### 有問題的 Server（把這個存成 bad_server.py）

```python
# bad_server.py — 這個 Server 有很多設計問題，你能找出來嗎？
from mcp.server.fastmcp import FastMCP
import json
import httpx

mcp = FastMCP("糟糕的服務")

PRODUCTS = {
    "P001": {"name": "鍵盤", "price": 1200, "stock": 50},
    "P002": {"name": "滑鼠", "price": 800, "stock": 30},
    "P003": {"name": "螢幕", "price": 8000, "stock": 10},
}

ORDERS = {}
next_order_id = 1

@mcp.tool()
def search(q: str, t: str = "p") -> str:
    """搜尋"""
    if t == "p":
        results = [
            {"id": pid, **info}
            for pid, info in PRODUCTS.items()
            if q.lower() in info["name"].lower()
        ]
        return str(results)  # 直接用 str()，不是 json.dumps
    return "不支援的類型"


@mcp.tool()
def getProduct(productId: str) -> str:
    """取得產品"""
    p = PRODUCTS.get(productId)
    if not p:
        raise ValueError(f"Product {productId} not found")  # raise exception！
    return json.dumps(p)


@mcp.tool()
def createOrder(productId: str, qty: int, userId: str) -> str:
    """下訂單"""
    global next_order_id
    p = PRODUCTS.get(productId)
    if not p:
        raise KeyError("product not found")
    if p["stock"] < qty:
        raise ValueError("not enough stock")
    p["stock"] -= qty
    order = {"id": f"ORD-{next_order_id:04d}", "product": productId, "qty": qty, "user": userId}
    ORDERS[order["id"]] = order
    next_order_id += 1
    return json.dumps(order)


@mcp.tool()
def cancelOrder(orderId: str) -> str:
    """取消訂單"""
    if orderId not in ORDERS:
        return "error"
    del ORDERS[orderId]
    return "ok"


@mcp.tool()
def updateStock(productId: str, newStock: int) -> str:
    """更新庫存"""
    if productId in PRODUCTS:
        PRODUCTS[productId]["stock"] = newStock
        return "updated"
    return "not found"


@mcp.tool()
def getAllProducts() -> str:
    """取得所有產品"""
    return str(PRODUCTS)


@mcp.tool()
def getOrderCount() -> str:
    """訂單數量"""
    return str(len(ORDERS))


if __name__ == "__main__":
    mcp.run()
```

### 你的任務

1. 先用 `mcp dev bad_server.py` 啟動 Inspector
2. 找出所有的設計問題（至少 8 個）
3. 參考下面的問題清單確認你是否都找到了
4. 重寫成 `good_server.py`

<details>
<summary>設計問題清單（先自己找，再對答案）</summary>

1. **工具名稱不一致**：`search`、`getProduct`（駝峰）、`createOrder`（駝峰）混用
2. **參數名稱縮寫**：`q`、`t` 完全看不懂
3. **Description 太爛**：「搜尋」、「取得產品」提供零資訊
4. **raise exception**：`getProduct` 和 `createOrder` 會拋出例外而不是回傳錯誤字串
5. **`str()` 不是 JSON**：`search` 和 `getAllProducts` 用 Python 的 `str()` 而不是 `json.dumps()`
6. **cancelOrder 的錯誤訊息無意義**：回傳 "error" 和 "ok"，AI 無法理解
7. **updateStock 未聲明副作用**：這個工具修改了庫存，但 description 沒有警告
8. **createOrder 未聲明副作用**：下訂單是不可逆的操作，沒有說明
9. **工具數量**：7 個工具，剛好在邊界（可以考慮合併）
10. **cancelOrder 沒有還原庫存**：取消訂單後庫存沒有增加回去（邏輯錯誤）

</details>

### 參考修復版本

```python
# good_server.py — 修復後的版本
from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("產品訂單服務")

PRODUCTS = {
    "P001": {"name": "鍵盤", "price": 1200, "stock": 50},
    "P002": {"name": "滑鼠", "price": 800, "stock": 30},
    "P003": {"name": "螢幕", "price": 8000, "stock": 10},
}

ORDERS = {}
next_order_id = 1


@mcp.tool()
def search_products(keyword: str) -> str:
    """
    依關鍵字搜尋產品。

    當使用者想找特定產品時呼叫此工具。
    keyword 是要搜尋的產品名稱關鍵字（中文或英文）。
    回傳符合條件的產品列表，包含 ID、名稱、價格和庫存數量。
    如果沒有找到，回傳空列表。
    """
    results = [
        {"product_id": pid, "name": info["name"],
         "price": info["price"], "stock": info["stock"]}
        for pid, info in PRODUCTS.items()
        if keyword.lower() in info["name"].lower()
    ]
    if not results:
        return f"沒有找到包含「{keyword}」的產品。請嘗試其他關鍵字，或用 list_all_products 查看所有產品。"
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def list_all_products() -> str:
    """
    列出所有可用產品的完整清單，包含 ID、名稱、價格和庫存。

    當使用者想瀏覽所有產品、或不確定要搜尋什麼關鍵字時呼叫此工具。
    """
    all_products = [
        {"product_id": pid, **info}
        for pid, info in PRODUCTS.items()
    ]
    return json.dumps(all_products, ensure_ascii=False, indent=2)


@mcp.tool()
def create_order(product_id: str, quantity: int, user_id: str) -> str:
    """
    為指定用戶建立產品訂單。⚠️  這是不可復原的操作。

    【僅在使用者明確確認要購買時呼叫此工具】
    不要在使用者只是詢問產品資訊或比較產品時呼叫。

    執行後會：(1) 扣減庫存 (2) 建立訂單記錄

    product_id：產品 ID（格式 P001、P002...），可用 list_all_products 查詢
    quantity：購買數量，必須是正整數
    user_id：用戶 ID 字串
    """
    global next_order_id

    if quantity <= 0:
        return f"錯誤：quantity 必須是正整數，但收到 {quantity}。"

    product = PRODUCTS.get(product_id)
    if not product:
        available = list(PRODUCTS.keys())
        return f"找不到 product_id={product_id} 的產品。可用的 ID：{available}"

    if product["stock"] < quantity:
        return (
            f"庫存不足！{product['name']} 目前庫存只有 {product['stock']} 件，"
            f"但您要購買 {quantity} 件。請減少購買數量。"
        )

    product["stock"] -= quantity
    order_id = f"ORD-{next_order_id:04d}"
    order = {
        "order_id": order_id,
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "total_price": product["price"] * quantity,
        "user_id": user_id,
    }
    ORDERS[order_id] = order
    next_order_id += 1

    return (
        f"訂單已成功建立！\n"
        + json.dumps(order, ensure_ascii=False, indent=2)
    )


@mcp.tool()
def cancel_order(order_id: str) -> str:
    """
    取消指定訂單並恢復庫存。⚠️  此操作不可復原。

    【僅在使用者明確確認要取消訂單時呼叫】
    取消後訂單記錄將被刪除，庫存將恢復。

    order_id：訂單 ID（格式 ORD-XXXX）
    """
    order = ORDERS.get(order_id)
    if not order:
        return (
            f"找不到訂單 {order_id}。"
            "可能原因：訂單 ID 不正確，或訂單已被取消。"
        )

    # 恢復庫存（這個是 bad_server.py 裡的邏輯錯誤！）
    product = PRODUCTS.get(order["product_id"])
    if product:
        product["stock"] += order["quantity"]

    del ORDERS[order_id]
    return (
        f"訂單 {order_id} 已成功取消。"
        f"{order['product_name']} x{order['quantity']} 件已恢復庫存。"
    )


if __name__ == "__main__":
    mcp.run()
```

---

## 重點回顧 📌

```
┌─────────────────────────────────────────────────────┐
│                  第三章重點回顧                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  • Description 是你和 AI 的合約：                   │
│    說清楚何時呼叫、何時不呼叫、參數如何使用         │
│                                                     │
│  • 五個設計陷阱：                                   │
│    1. Description 太模糊                            │
│    2. 工具數量超過 7 個（造成 AI 選擇混亂）         │
│    3. 參數命名不一致（user_id vs userId vs uid）    │
│    4. 錯誤訊息對 AI 沒意義（"Error 500" vs 具體說明）│
│    5. 副作用未聲明（刪除、付款、發送）              │
│                                                     │
│  • 錯誤回傳設計：                                   │
│    不要 raise exception，回傳有意義的錯誤字串       │
│    好錯誤訊息：發生什麼 + 可能原因 + 建議下一步     │
│                                                     │
│  • 工具拆分決策：                                   │
│    功能不同 → 拆開；場景重疊 → 合併；≤7 個工具     │
│                                                     │
│  • MCP Inspector：                                  │
│    mcp dev server.py                                │
│    先用 Inspector 測試，再接 Claude Desktop         │
│    測試正常、邊界、錯誤三種情況                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 常見問題 FAQ

**Q1：如果我有 10 個工具，但每個都有不同的場景，可以不拆 Server 嗎？**

可以，但要非常謹慎。關鍵是：每個工具的 description 都要寫得非常清楚，讓 AI 在 10 個工具中能準確判斷要用哪一個。建議你用 Inspector 模擬幾個使用場景，手動判斷「如果我是 AI，看到這些 description，我能選到正確的工具嗎？」如果答案是是，就沒問題。

**Q2：我的工具有很多可選參數，要在 description 裡全部說明嗎？**

重要的參數要說明，次要的可以簡短帶過。但任何有特定格式要求的參數（例如日期格式、ID 格式、枚舉值）一定要說明清楚。AI 不會猜——如果你不說，它要麼不呼叫，要麼傳入錯誤格式。

**Q3：工具的回傳值需要固定格式嗎？**

不需要固定格式，但要一致。同一個工具在成功和失敗時的回傳格式最好一致——例如成功時回傳 JSON，失敗時也用 JSON 格式（帶一個 "error" 欄位），這樣 AI 更容易解析。或者成功和失敗都用純文字字串，同樣可以。混用 JSON 和純文字比較容易讓 AI 困惑。

**Q4：我可以在 description 裡用中文嗎？**

完全可以！實際上，如果你的使用者說中文，把 description 也寫成中文是個好主意。AI（特別是多語言模型）在看到使用者說中文、工具 description 也是中文時，往往能做出更準確的工具選擇判斷。

---

## 課後練習

### ⭐ 基礎練習：Description 改寫

找出第二章你寫的 `calculate_stats` 工具，按照本章的原則重寫它的 description：

- 加上「何時呼叫」的觸發條件（至少 3 種情境）
- 加上「何時不要呼叫」的排除條件
- 詳細說明每個參數的格式和範例
- 說明回傳值的格式

### ⭐⭐ 進階練習：設計一組工具

為一個「會議助理」設計工具集（不需要實作，只需要設計）：

設計 4-6 個工具，每個工具包含：
- 名稱（snake_case）
- 完整的 description（按照本章原則）
- 參數列表（名稱、型別、說明）
- 副作用說明（如果有的話）

考慮：哪些功能應該是 Tool？哪些應該是 Resource？

### ⭐⭐⭐ 挑戰練習：對抗 Prompt Injection

Prompt Injection 是 MCP 工具的一個安全威脅：攻擊者在輸入的文字裡藏入指令，試圖讓 AI 執行非預期的動作。

研究 Prompt Injection 攻擊（搜尋 "prompt injection MCP security"），然後：

1. 設計一個故意有 Prompt Injection 漏洞的工具（只是展示，不要真的部署）
2. 說明攻擊者如何利用這個漏洞
3. 設計防禦機制（輸入驗證、輸出過濾、操作白名單）
4. 實作帶防禦機制的安全版本

---

## 下一章預告

你已經能設計出 Claude 正確使用的 Tools 了。但 MCP 還有另外兩個原語——Resources 和 Prompts——讓你能做更多事。

第四章，我們要學習怎麼把你的資料庫 Schema、設定檔、向量資料集暴露為可瀏覽的 Resources，以及怎麼把常用的分析流程打包成 Prompts，讓 Claude Desktop 的「/」選單為你所用。

→ [第四章：Resources 與 Prompts](./ch04-resources-prompts.md)

← [第二章：打造你的第一個工具](./ch02-first-tool.md)
