# 資訊管理系完全學習手冊（教案整合版）
### 理論 × 實作 × 職涯 — Project-First 整合課程

---

> **給學習者的話**
>
> 這本手冊不是課本，是你的**工作台**。每個單元都有明確的目標、課堂流程、可執行的程式碼、作業規格與評分規準。
>
> 貫穿全課的核心節奏只有一句話：
> **概念（Why）→ 示範（How）→ 練習（Do）→ 反思（Improve）→ 提交（Ship）**
>
> 每次產出都進 GitHub。四年後，你的倉庫就是你的履歷。

---

## 目錄

- [Unit 0：課程設定與學習契約](#unit-0)
- [Unit 1：計算思維與效能直覺](#unit-1)
- [Unit 2：資料結構選型與小系統](#unit-2)
- [Unit 3：系統常識——OS、Thread、HTTP](#unit-3)
- [Unit 4：Python 進階與程式碼品質](#unit-4)
- [Unit 5：Git 與作品集系統化](#unit-5)
- [Unit 6：系統設計入門](#unit-6)
- [Unit 7：關聯式資料庫與 SQL](#unit-7)
- [Unit 8：資料分析與視覺化](#unit-8)
- [Unit 9：NoSQL 選型與快取思維](#unit-9)
- [Unit 10：系統分析與資安基礎](#unit-10)
- [Unit 11：敏捷開發與專案管理](#unit-11)
- [Unit 12：AI 整合與職涯路線](#unit-12)
- [期末整合專案規格](#capstone)
- [作品集結構建議](#portfolio)

---

# Unit 0：課程設定與學習契約 {#unit-0}

## 學習成果（Course Outcomes）

完成本課後，你能：

1. 用計算思維把真實問題拆解成可實作任務
2. 用 Python 寫出可維護的程式（不只是會跑）
3. 選對資料結構、理解時間複雜度並做簡單效能測試
4. 懂 HTTP / API 基礎，能呼叫與設計 REST API
5. 設計關聯式資料庫 schema、寫 SQL（含 JOIN、聚合、視窗函數）
6. 用 pandas 完成分析與視覺化，並寫出可讀報告
7. 理解常見資安風險並避免基本漏洞
8. 產出可上 GitHub 的作品集（含 README 與規格文件）
9. 把能力對應到職涯路徑（工程 / 資料 / 顧問PM / 資安 / AI整合）

## 課程產出（Artifacts）

| 產出物 | 說明 |
|--------|------|
| `im-learning-portfolio` GitHub repo | 必備，所有章節成果放這裡 |
| 每章資料夾 + README | 記錄你學了什麼、遇到什麼坑 |
| 期末整合專案 | 含設計文件、API、DB、分析、資安檢核 |
| 個人職涯路線圖（1頁） | 路徑選擇 + 8 週補強計畫 |

## 評量設計

| 項目 | 比例 |
|------|------|
| 平時練習提交（小作業） | 40% |
| 單元專案（中作業） | 30% |
| 期末整合專案 | 25% |
| 學習反思與職涯路線圖 | 5% |

## 主線專案的演進

```
Lesson 4   →  圖書館管理系統（資料結構）
Lesson 17  →  短網址服務（系統設計）
Lesson 21  →  電商 DB 模型（資料庫）
Lesson 24  →  銷售分析報告（資料分析）
Lesson 29  →  資安強化版登入（資安）
Lesson 35  →  期末 Demo Day（全整合）
```

---

# Unit 1：計算思維與效能直覺 {#unit-1}

## Lesson 1：計算思維——先中文，後程式

### 學習目標

- 能用「分解、模式、抽象、演算法」四個步驟描述問題
- 能在打開編輯器之前，先寫出中文解題步驟

### 課堂流程（建議 90 分鐘）

| 時間 | 活動 |
|------|------|
| 0–10m | 情境引導：為何語法不是核心，核心是拆解 |
| 10–30m | 四大能力講解：Decomposition / Pattern / Abstraction / Algorithm |
| 30–40m | 示範：把「訂餐系統」拆成模組 |
| 40–70m | 實作：練習 1-1（中文演算法） |
| 70–85m | 同儕互評：交換步驟，看誰更清楚、更可實作 |
| 85–90m | 轉成 Python + commit |

### 四大計算思維能力

```
分解（Decomposition）
    把複雜問題拆解成小問題
    例：「建一個訂餐系統」
    → 使用者管理 + 菜單管理 + 訂單管理 + 支付流程

模式識別（Pattern Recognition）
    在問題中找到相似的結構或規律
    例：「這個問題跟我之前做的圖書館借還很像，
         可以用同樣的狀態機邏輯解決」

抽象化（Abstraction）
    忽略不重要的細節，專注核心概念
    例：「我不需要知道 Python 底層怎麼管記憶體，
         但我需要知道什麼時候用 list vs dict」

演算法思維（Algorithm Design）
    設計可重複執行、有明確輸入輸出的步驟序列
    例：設計「每天早上自動抓股價並 email 給自己」的流程
```

### 實作練習 1-1：用中文寫演算法

**題目**：你有一個班級的考試分數列表，要計算：平均分、最高分、最低分，以及有多少人不及格（低於 60 分）。

**規則**：先不要打開 IDE，在任何編輯器裡，用**中文**把解題步驟寫清楚。

範例格式：

```
【我的中文演算法】
輸入：包含所有學生分數的清單

步驟 1 — 計算平均分：
  1.1 設定總和變數，初始值為 0
  1.2 逐一取出每個分數，累加到總和
  1.3 總和 ÷ 分數個數 = 平均分

步驟 2 — 找最高分：
  2.1 設定「目前最大值」，初始值為清單第一個數字
  2.2 逐一比較剩餘分數，若大於「目前最大值」就更新

步驟 3 — 找最低分：
  3.1 邏輯同步驟 2，方向相反

步驟 4 — 計算不及格人數：
  4.1 設定計數器，初始值為 0
  4.2 逐一檢查每個分數
  4.3 若分數 < 60，計數器 +1

輸出：平均分、最高分、最低分、不及格人數
```

**然後**，把中文步驟翻成 Python：

```python
def analyze_scores(scores: list[float]) -> dict:
    """
    分析一組分數，回傳統計結果。
    
    Args:
        scores: 分數清單（假設不為空）
    Returns:
        包含 average, max, min, fail_count 的字典
    """
    if not scores:
        raise ValueError("分數清單不可為空")
    
    total = sum(scores)
    average = total / len(scores)
    max_score = max(scores)
    min_score = min(scores)
    fail_count = sum(1 for s in scores if s < 60)
    
    return {
        "average": round(average, 2),
        "max": max_score,
        "min": min_score,
        "fail_count": fail_count,
        "fail_rate": f"{fail_count / len(scores):.1%}"
    }

# 測試
scores = [85, 92, 55, 78, 43, 96, 67, 58, 88, 72]
result = analyze_scores(scores)
for key, value in result.items():
    print(f"{key}: {value}")
```

### 課後作業

提交到 `ch01-computational-thinking/` 資料夾：

1. `algorithm_chinese.md`：你的中文演算法步驟
2. `score_analyzer.py`：轉換後的 Python 程式
3. 在 README 回答：**你在哪個步驟做了抽象？忽略了哪些細節？原因是什麼？**

### 評分規準（滿分 10 分）

| 項目 | 分數 |
|------|------|
| 中文步驟清晰、可執行（不含模糊描述） | 4 |
| Python 程式正確，有適當錯誤處理 | 3 |
| 命名清楚、有 docstring | 2 |
| README 反思有實質內容 | 1 |

---

## Lesson 2：Big-O 與效能直覺——跑一次就懂

### 學習目標

- 直覺理解 O(1)、O(n)、O(n²) 的速度差距
- 能用簡單 benchmark 驗證效能差異
- 能在寫程式時問自己：「這裡的複雜度是多少？」

### 課堂流程（建議 90 分鐘）

| 時間 | 活動 |
|------|------|
| 0–15m | Big-O 表格導讀與直覺建立 |
| 15–25m | 反例故事：訂單 10 萬筆兩層迴圈爆炸 |
| 25–40m | 範例程式解讀：slow vs fast 找重複 |
| 40–75m | 實作：練習 1-2 benchmark，自己跑、記數字 |
| 75–85m | 延伸：把 data 改到 50,000 筆，觀察差距加速 |
| 85–90m | 把 benchmark 輸出貼到 README |

### Big-O 直覺速查表

| 複雜度 | 中文解釋 | 實際例子 | 10 萬筆資料大約多快 |
|--------|---------|---------|-----------------|
| O(1) | 不管資料多少，速度一樣 | dict 查值 | 瞬間 |
| O(log n) | 每次排除一半 | 二元搜尋 | 約 17 步 |
| O(n) | 資料多一倍，時間多一倍 | 掃描找最大值 | 約 0.1 秒 |
| O(n log n) | 略多於線性 | 快速排序 | 約 1.7 秒 |
| O(n²) | 資料多一倍，時間多四倍 | 兩層 for 迴圈 | 約 2.8 小時 |
| O(2ⁿ) | 指數爆炸 | 暴力破解密碼 | 宇宙年齡不夠 |

### 反例：你以為快，其實很慢

```python
# 情境：訂單系統要找出重複的訂單 ID
# 資料很少時沒人發現問題，資料一多就爆炸

# ❌ O(n²)：兩層迴圈 — 資料一多就死
def find_duplicates_slow(orders: list) -> list:
    duplicates = []
    for i in range(len(orders)):
        for j in range(i + 1, len(orders)):  # 每個元素都和其他所有元素比
            if orders[i] == orders[j]:
                duplicates.append(orders[i])
    return duplicates

# ✅ O(n)：用 set 做到線性時間
def find_duplicates_fast(orders: list) -> list:
    seen = set()
    duplicates = set()
    for order in orders:
        if order in seen:   # set 的 in 操作是 O(1)
            duplicates.add(order)
        seen.add(order)
    return list(duplicates)
```

### 實作練習 1-2：效能 Benchmark

**目標**：親眼看見兩者的速度差距，感受一次 O(n²) 的代價。

```python
import time
import random

def benchmark(func, data, label: str):
    start = time.time()
    result = func(data)
    elapsed = time.time() - start
    print(f"  {label:25s}: {elapsed:.4f} 秒，找到 {len(result)} 個重複")

# 生成測試資料
print("生成資料中...")
data_1k   = [random.randint(1, 800)  for _ in range(1_000)]
data_10k  = [random.randint(1, 8000) for _ in range(10_000)]
data_30k  = [random.randint(1, 25000) for _ in range(30_000)]

for label, data in [("1,000 筆", data_1k), 
                    ("10,000 筆", data_10k),
                    ("30,000 筆", data_30k)]:
    print(f"\n=== {label} ===")
    benchmark(find_duplicates_slow, data, "❌ 慢版本 O(n²)")
    benchmark(find_duplicates_fast, data, "✅ 快版本 O(n)")
```

把輸出貼到你的 README，格式如下：

```markdown
## Benchmark 結果（2025-XX-XX，M1 MacBook）

| 資料量 | 慢版本 O(n²) | 快版本 O(n) | 倍數差距 |
|--------|------------|------------|---------|
| 1,000  | 0.0XXX 秒 | 0.0001 秒 | XX 倍   |
| 10,000 | X.XXX 秒  | 0.001 秒  | XX 倍   |
| 30,000 | XX.XX 秒  | 0.003 秒  | XX 倍   |

**結論**：O(n²) 在資料量增加 30 倍時，耗時增加了約 _____ 倍；
而 O(n) 幾乎是線性成長。
```

### 課後作業

**進階版**：把 `orders` 改成 list of dict（模擬真實訂單），找出重複的 `order_id`：

```python
# 輸入格式
orders = [
    {"order_id": "ORD-001", "customer": "王小明", "amount": 3200},
    {"order_id": "ORD-002", "customer": "李小花", "amount": 1500},
    {"order_id": "ORD-001", "customer": "王小明", "amount": 3200},  # 重複！
    # ... 更多訂單
]

# 你的任務：
# 1. 用 O(n) 找出重複的 order_id
# 2. 在 README 解釋：為何 set 能做到 O(1) 的 in 操作？
#    （提示：hash table 的原理）
```

---

# Unit 2：資料結構選型與小系統 {#unit-2}

## Lesson 3：資料結構選型——選對容器，事半功倍

### 學習目標

- 知道 list / dict / set / queue / stack / tree 各自的使用情境
- 能做「需求 → 結構 → 理由」的選型說明

### 課堂流程（建議 90 分鐘）

| 時間 | 活動 |
|------|------|
| 0–25m | 快速導覽六種結構（各 4 分鐘） |
| 25–45m | 迷你選型題（分組討論） |
| 45–75m | 實作：把決策表變成你自己的 Markdown |
| 75–90m | 提交 `decision-table.md` |

### 六種核心資料結構

**1. List（列表）— 有序、可索引**

```python
scores = [85, 92, 78, 65, 90]

# ✅ 適合：有順序、需要位置索引、需要排序
# ❌ 不適合：頻繁中間插入/刪除（O(n)）

import statistics
print(f"平均：{statistics.mean(scores)}")       # 87.6
print(f"中位數：{statistics.median(scores)}")   # 85.0
```

**2. Dict（字典）— 名稱查值，O(1)**

```python
student = {
    "id": "B10901234",
    "name": "王小明",
    "gpa": 3.7,
    "courses": ["資料庫", "程式設計", "統計學"]
}

# ✅ 適合：快速用 key 查詢 value、計數、去重後保留值
# ❌ 不適合：需要按插入「順序之外」排序

students_db = {"B10901234": {"name": "王小明", "gpa": 3.7}}
student = students_db.get("B10901234")  # O(1)，不管有多少筆
```

**3. Set（集合）— 去重與快速成員判斷**

```python
registered = {"資料庫", "程式設計", "統計學"}
available  = {"資料庫", "演算法", "網路概論", "統計學"}

# 還可以選哪些課？
can_register = available - registered
print(can_register)   # {'演算法', '網路概論'}

# 兩個系統的共同用戶
sys_a = {"alice", "bob", "charlie"}
sys_b = {"bob", "charlie", "eve"}
common = sys_a & sys_b
print(common)   # {'bob', 'charlie'}
```

**4. Queue（佇列）— 先進先出（FIFO）**

```python
from collections import deque

# ✅ 適合：客服排隊、任務排程、BFS 搜尋
support_queue = deque()
support_queue.append("客戶A")   # 加入排隊
support_queue.append("客戶B")
support_queue.append("客戶C")
next_customer = support_queue.popleft()  # 先來先服務
print(next_customer)  # 客戶A
```

**5. Stack（堆疊）— 後進先出（LIFO）**

```python
# ✅ 適合：undo/redo、瀏覽器上一頁、程式遞迴追蹤
browser_history = []
browser_history.append("google.com")
browser_history.append("youtube.com")
browser_history.append("github.com")
back = browser_history.pop()  # 回到上一頁
print(back)  # github.com
```

**6. Tree（樹）— 階層結構**

```python
class TreeNode:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []

# ✅ 適合：組織架構、檔案系統、商品分類、HTML DOM
ceo = TreeNode("執行長")
vp_tech = TreeNode("技術副總")
vp_biz  = TreeNode("業務副總")
vp_tech.children = [TreeNode("工程師A"), TreeNode("工程師B")]
vp_biz.children  = [TreeNode("業務員A")]
ceo.children     = [vp_tech, vp_biz]

def print_tree(node, level=0):
    print("  " * level + node.name)
    for child in node.children:
        print_tree(child, level + 1)

print_tree(ceo)
```

### 選型決策表

```
你的需求是…
│
├─ 快速用「名稱/ID」查詢          → dict
├─ 有序、需要索引位置              → list
├─ 去重複 / 快速判斷是否存在       → set
├─ 先進先出（排隊、任務佇列）       → deque（queue）
├─ 後進先出（undo、遞迴回溯）       → list（當 stack）
└─ 階層關係（分類、組織、路徑）     → tree
```

### 課後作業

`ch02-data-structures/decision-table.md`

寫出 5 個「真實情境 → 結構選擇」案例，每個包含：

1. 情境描述（一句話）
2. 選哪個結構
3. 為什麼（性能/語意/方便性各選一個理由）

---

## Lesson 4：小專案——圖書館管理系統

### 學習目標

- 用 dict + set + list 實作一個可運作的小系統
- 能設計方法與狀態，處理借書 / 還書 / 搜尋 / 查詢

### 課堂流程（建議 120 分鐘）

| 時間 | 活動 |
|------|------|
| 0–10m | 需求重述（5 個功能逐一確認） |
| 10–25m | 設計討論：哪些狀態用 set？哪些用 dict？ |
| 25–95m | 實作：完成骨架 + 自己加 1 個新功能 |
| 95–110m | Demo：每人展示一次完整借還流程 |
| 110–120m | 打 tag `v0.1-library` 並 push |

### 完整實作骨架

```python
"""
圖書館管理系統
需求：
  1. 新增書籍
  2. 借書（同一本書不能借兩次）
  3. 還書
  4. 搜尋書名包含關鍵字的書
  5. 查看某位讀者目前借了哪些書
"""

class Library:
    def __init__(self):
        self.books: dict = {}        # {書號: {"title": ..., "author": ...}}
        self.borrowed: set = set()   # 目前借出的書號（O(1) 查詢）
        self.records: dict = {}      # {讀者名稱: [書號列表]}
    
    def add_book(self, book_id: str, title: str, author: str) -> None:
        self.books[book_id] = {"title": title, "author": author}
        print(f"✅ 新增：《{title}》({book_id})")
    
    def borrow_book(self, book_id: str, borrower: str) -> bool:
        if book_id not in self.books:
            print(f"❌ 書號 {book_id} 不存在")
            return False
        if book_id in self.borrowed:
            title = self.books[book_id]["title"]
            print(f"❌ 《{title}》目前已被借出")
            return False
        
        self.borrowed.add(book_id)
        self.records.setdefault(borrower, []).append(book_id)
        print(f"✅ {borrower} 借閱《{self.books[book_id]['title']}》成功")
        return True
    
    def return_book(self, book_id: str, borrower: str) -> bool:
        if book_id not in self.borrowed:
            print(f"❌ 書號 {book_id} 沒有借出記錄")
            return False
        
        self.borrowed.discard(book_id)
        if borrower in self.records and book_id in self.records[borrower]:
            self.records[borrower].remove(book_id)
        
        print(f"✅ 《{self.books[book_id]['title']}》已歸還")
        return True
    
    def search(self, keyword: str) -> list:
        results = []
        for book_id, info in self.books.items():
            if keyword.lower() in info["title"].lower():
                status = "已借出" if book_id in self.borrowed else "可借閱"
                results.append({
                    "book_id": book_id,
                    "title": info["title"],
                    "author": info["author"],
                    "status": status
                })
        return results
    
    def get_borrower_books(self, borrower: str) -> list:
        ids = self.records.get(borrower, [])
        return [self.books[bid]["title"] for bid in ids if bid in self.books]


# ── 測試腳本 ──
lib = Library()
lib.add_book("B001", "Python 程式設計", "王大明")
lib.add_book("B002", "資料庫設計與應用", "李小花")
lib.add_book("B003", "Python 資料分析", "張三")

print("\n--- 借書測試 ---")
lib.borrow_book("B001", "陳同學")
lib.borrow_book("B001", "林同學")   # 應該失敗

print("\n--- 搜尋測試 ---")
for book in lib.search("Python"):
    print(f"  [{book['status']}] {book['title']} — {book['author']}")

print(f"\n陳同學借閱中：{lib.get_borrower_books('陳同學')}")

lib.return_book("B001", "陳同學")
lib.borrow_book("B001", "林同學")   # 現在應該成功
```

### 加分擴充（選做）

| 功能 | 提示 |
|------|------|
| 借閱期限 | 在 records 存 `(book_id, due_date)`；還書時提醒逾期 |
| 搜尋作者 | 讓 search 同時比對 title 和 author |
| 防呆還書 | return 時若 borrower 不符，拒絕並說明 |
| 統計報表 | `print_stats()` 顯示總書數、借出數、熱門書 |

### 評分規準（滿分 15 分）

| 項目 | 分數 |
|------|------|
| 5 個功能全部正確 | 8 |
| 新增自訂功能（有測試） | 3 |
| 程式碼風格與命名 | 2 |
| `v0.1-library` tag 已 push | 1 |
| README 有說明設計決策（選哪個結構、為何） | 1 |

---

# Unit 3：系統常識——OS、Thread、HTTP {#unit-3}

## Lesson 5：Process vs Thread——Race Condition 的真實感

### 學習目標

- 理解 process / thread 的差異
- 知道 race condition 的成因與 lock 的作用
- 體驗「程式看起來對，但多執行緒就爆」

### 課堂流程（建議 90 分鐘）

| 時間 | 活動 |
|------|------|
| 0–10m | 問題引入：為什麼結果不是 200000？ |
| 10–30m | 圖解：讀取 → +1 → 寫入（三步驟競爭） |
| 30–50m | 程式逐行解讀（unsafe vs lock） |
| 50–75m | 實作：改成 4 個 threads，觀察結果 |
| 75–85m | 討論：lock 的代價是什麼？ |
| 85–90m | commit `thread_race.py` |

### 核心程式碼

```python
import threading
import time

# ═══════════════════════════════════════
# ❌ 危險示範：Race Condition
# ═══════════════════════════════════════
counter_unsafe = 0

def increment_unsafe():
    global counter_unsafe
    for _ in range(100_000):
        # 這一行在 CPU 層級分三步：讀取、加1、寫入
        # 若兩個 thread 同時進行，就會「互蓋」
        counter_unsafe += 1

t1 = threading.Thread(target=increment_unsafe)
t2 = threading.Thread(target=increment_unsafe)
t1.start(); t2.start()
t1.join();  t2.join()
print(f"[不安全] 結果：{counter_unsafe}（預期 200000，通常偏少）")

# ═══════════════════════════════════════
# ✅ 正確做法：使用 Lock
# ═══════════════════════════════════════
counter_safe = 0
lock = threading.Lock()

def increment_safe():
    global counter_safe
    for _ in range(100_000):
        with lock:   # 確保同一時間只有一個 thread 修改
            counter_safe += 1

t3 = threading.Thread(target=increment_safe)
t4 = threading.Thread(target=increment_safe)
t3.start(); t4.start()
t3.join();  t4.join()
print(f"[安全]   結果：{counter_safe}（永遠是 200000）")
```

### 實作挑戰

1. 把執行緒數改成 4，觀察不安全版本的誤差更大嗎？
2. 用 `time.time()` 計時，比較加鎖前後的速度差距
3. 在 README 回答：**為什麼「加鎖讓程式正確」，但「加太多鎖讓程式慢」？**

---

## Lesson 6：HTTP 旅程與狀態碼

### 學習目標

- 能說清楚一次 HTTPS 請求從 DNS 到回應的完整旅程
- 能用狀態碼判斷問題所在

### HTTP 請求的完整旅程

```
你在瀏覽器輸入：https://api.example.com/users/123

第一步：DNS 查詢
  → 把 api.example.com 翻譯成 IP 位址（如 93.184.216.34）
  → 你的電腦先查本機快取 → 再查 ISP → 再查根伺服器

第二步：TCP 三次握手（建立可靠連線）
  → 客戶端：SYN（我要連線）
  → 伺服器：SYN-ACK（好，我收到了）
  → 客戶端：ACK（確認）

第三步：TLS 握手（因為是 HTTPS，需要加密）
  → 交換憑證、協商加密演算法
  → 之後所有資料都加密傳輸

第四步：HTTP 請求送出
  GET /users/123 HTTP/1.1
  Host: api.example.com
  Authorization: Bearer eyJhbGci...
  Content-Type: application/json

第五步：伺服器處理
  → 解析請求 → 查資料庫 → 組回應

第六步：HTTP 回應
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {"id": 123, "name": "王小明"}
```

### 狀態碼速查與情境對應

| 狀態碼 | 意義 | 你的程式什麼時候會看到它 |
|--------|------|----------------------|
| **200** | 成功 | 正常 GET/POST |
| **201** | 已建立 | POST 新增資料成功 |
| **204** | 成功，無內容 | DELETE 成功 |
| **400** | 請求格式錯誤 | 你送的 JSON 格式不對、缺少必填欄位 |
| **401** | 未授權 | 沒帶 token 或 token 過期 |
| **403** | 禁止存取 | 帶了 token 但沒有這個操作的權限 |
| **404** | 找不到 | 資源不存在（ID 錯了） |
| **409** | 衝突 | 要建立的資源已存在（如 email 重複） |
| **422** | 無法處理 | 格式對了但語意錯（如日期不合邏輯） |
| **429** | 請求過多 | 你超過了 API 速率限制 |
| **500** | 伺服器錯誤 | 後端程式出 bug |
| **502** | 閘道錯誤 | 上游服務沒回應 |
| **503** | 服務不可用 | 伺服器在維護或太忙 |

### 情境判斷練習

給你以下 5 個情境，說出正確狀態碼：

1. 用戶嘗試登入，帳號不存在
2. 管理員刪除了一篇文章
3. 用戶嘗試存取別人的私人訊息（已登入但沒權限）
4. 用戶送出的 email 格式不對（缺少 @）
5. 資料庫連線中斷，所有查詢都失敗

*(答案：404 / 204 / 403 / 400 / 503)*

---

## Lesson 7：呼叫真實 API——requests + JSON

### 學習目標

- 能發出 GET / POST 請求，正確處理 headers / params / json body
- 能用狀態碼做錯誤分支

### 課堂流程（建議 90 分鐘）

| 時間 | 活動 |
|------|------|
| 0–15m | 示範 JSONPlaceholder（免費公開 API） |
| 15–65m | 實作：完成 3 個函式 |
| 65–80m | 擴充：把結果存成 `output.json` |
| 80–90m | commit `api_client.py` |

### 完整實作

```python
"""
實作目標：
  1. get_user(user_id) — GET 查詢使用者
  2. get_user_posts(user_id) — GET 查詢使用者文章
  3. create_post(user_id, title, body) — POST 建立文章
  4. save_to_file(data, filepath) — 存成 JSON 檔
"""
import requests
import json
from typing import Optional

BASE_URL = "https://jsonplaceholder.typicode.com"

def get_user(user_id: int) -> Optional[dict]:
    """取得使用者資料，不存在回傳 None"""
    response = requests.get(f"{BASE_URL}/users/{user_id}")
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print(f"⚠️  使用者 {user_id} 不存在")
        return None
    else:
        raise Exception(f"API 錯誤：{response.status_code}")

def get_user_posts(user_id: int) -> list:
    """取得使用者所有文章"""
    response = requests.get(
        f"{BASE_URL}/posts",
        params={"userId": user_id}  # 自動轉為 ?userId=1
    )
    if response.status_code == 200:
        return response.json()
    return []

def create_post(user_id: int, title: str, body: str) -> dict:
    """建立新文章（POST 請求）"""
    response = requests.post(
        f"{BASE_URL}/posts",
        json={"userId": user_id, "title": title, "body": body},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 201:
        return response.json()
    raise Exception(f"建立失敗：{response.status_code} {response.text}")

def save_to_file(data, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 已儲存到 {filepath}")

# ── 主程式 ──
if __name__ == "__main__":
    # 取得使用者 1
    user = get_user(1)
    if user:
        print(f"使用者：{user['name']} ({user['email']})")
    
    # 取得其文章
    posts = get_user_posts(1)
    print(f"共 {len(posts)} 篇文章")
    if posts:
        print(f"第一篇標題：{posts[0]['title']}")
    
    # 建立新文章
    new_post = create_post(
        user_id=1,
        title="我在資管系學到的第一件事",
        body="在打開 IDE 之前，先用中文把解題步驟寫清楚。"
    )
    print(f"新文章 ID：{new_post['id']}")
    
    # 儲存結果
    save_to_file({
        "user": user,
        "posts": posts[:3],  # 只存前 3 篇
        "new_post": new_post
    }, "output.json")
    
    # 顯示請求詳細資訊
    r = requests.get(f"{BASE_URL}/users/1")
    print(f"\n請求耗時：{r.elapsed.total_seconds():.3f} 秒")
    print(f"Content-Type：{r.headers.get('Content-Type')}")
```

### 課後作業

把 `create_post` 的 body 改成讀取本地 `post.md` 的內容：

```python
def create_post_from_file(user_id: int, title: str, md_filepath: str) -> dict:
    """
    讀取 Markdown 檔案的內容作為文章 body
    練習：file I/O + requests POST
    """
    with open(md_filepath, "r", encoding="utf-8") as f:
        body = f.read()
    return create_post(user_id, title, body)
```

---

---

# Unit 4：Python 進階與程式碼品質 {#unit-4}

## Lesson 8：Pythonic 寫法——comprehension / zip / dict

### 學習目標

- 能把冗長迴圈改成 list comprehension 和 dict comprehension
- 能讀懂別人寫的 Pythonic 程式碼

### 三種常見 Comprehension

```python
# ─────────────────────────────────────
# 1. List Comprehension
# ─────────────────────────────────────

# 初學者版本
squares = []
for i in range(1, 11):
    if i % 2 == 0:
        squares.append(i ** 2)

# Pythonic 版本（一行，更易讀）
squares = [i**2 for i in range(1, 11) if i % 2 == 0]
print(squares)  # [4, 16, 36, 64, 100]

# ─────────────────────────────────────
# 2. Dict Comprehension
# ─────────────────────────────────────

students = ["Alice", "Bob", "Charlie"]
scores   = [85, 92, 78]

# 初學者版
grade_dict = {}
for i in range(len(students)):
    grade_dict[students[i]] = scores[i]

# Pythonic 版（用 zip 配對）
grade_dict = {name: score for name, score in zip(students, scores)}
print(grade_dict)  # {'Alice': 85, 'Bob': 92, 'Charlie': 78}

# ─────────────────────────────────────
# 3. 條件表達式（三元運算子）
# ─────────────────────────────────────

# 初學者版
grade_labels = []
for score in scores:
    if score >= 90:
        grade_labels.append("A")
    else:
        grade_labels.append("B")

# Pythonic 版
grade_labels = ["A" if s >= 90 else "B" for s in scores]
```

### 課堂小改寫練習

把以下三段「初學者版」改成 Pythonic 版本：

```python
# 題目 1：找出所有奇數並取平方
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result = []
for n in numbers:
    if n % 2 != 0:
        result.append(n * n)

# 題目 2：把課名和學分配成字典
course_names   = ["資料庫", "演算法", "統計學"]
course_credits = [3, 3, 2]
courses = {}
for i in range(len(course_names)):
    courses[course_names[i]] = course_credits[i]

# 題目 3：把每個字串轉大寫並過濾短於 4 字元的
words = ["python", "is", "fun", "and", "powerful"]
result = []
for w in words:
    if len(w) >= 4:
        result.append(w.upper())
```

---

## Lesson 9：Generator——大資料的記憶體救星

### 學習目標

- 理解 generator 的「固定記憶體」優勢
- 能寫出 `sum(1 for line in f if ...)` 這種慣用模式

### 記憶體問題的真實情境

```python
import time
import sys

# ─────────────────────────────────────
# 問題：讀取 100 萬行的 log 檔案
# ─────────────────────────────────────

# ❌ 把整個檔案讀進記憶體（資料一大就 OOM）
def read_all_logs_bad(filepath):
    with open(filepath) as f:
        return f.readlines()  # 100 萬行全在記憶體裡

# ✅ 用 generator 一行一行處理（記憶體用量固定）
def read_logs_generator(filepath):
    with open(filepath) as f:
        for line in f:
            yield line.strip()

# ─────────────────────────────────────
# Generator expression（更簡潔）
# ─────────────────────────────────────

def count_errors(filepath):
    with open(filepath) as f:
        # 不管檔案多大，這個函式的記憶體用量幾乎不變
        return sum(1 for line in f if "ERROR" in line)

# ─────────────────────────────────────
# 直觀示範：生成器 vs 列表的記憶體差距
# ─────────────────────────────────────

# 列表：全部存在記憶體
numbers_list = [i * i for i in range(1_000_000)]
print(f"列表記憶體：{sys.getsizeof(numbers_list):,} bytes")  # 約 8 MB

# 生成器：只記住「如何計算下一個值」
numbers_gen = (i * i for i in range(1_000_000))
print(f"生成器記憶體：{sys.getsizeof(numbers_gen)} bytes")   # 只有 104 bytes！

# 兩者的計算結果相同
print(sum(numbers_list) == sum(numbers_gen))  # True
```

### 課堂作業

生成一個假 log 檔（10 萬行），比對兩種讀法：

```python
import random
import os

# 生成假 log
def generate_fake_log(filepath, n_lines=100_000):
    levels = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]
    with open(filepath, "w") as f:
        for i in range(n_lines):
            level = random.choice(levels)
            f.write(f"2025-01-{(i%30)+1:02d} {level} 請求 {i} 處理{'完成' if level != 'ERROR' else '失敗'}\n")
    print(f"✅ 已生成 {filepath}（{n_lines} 行）")

generate_fake_log("app.log")

# 你的任務：比較以下兩種寫法的執行時間
# 1. readlines() 版本（把全部讀進 list 再過濾）
# 2. generator 版本（一行一行讀）
# 並用 time.time() 記錄時間，把結果貼到 README
```

---

## Lesson 10：Decorator / Context Manager——工程手感

### 學習目標

- 知道 decorator 用來「不改原函數卻改行為」
- 能用 `with` 保證資源釋放，不管有沒有例外

### Decorator：給函數加能力

```python
import time
import functools

# ─────────────────────────────────────
# 計時裝飾器
# ─────────────────────────────────────
def timer(func):
    @functools.wraps(func)   # 保留原函數的 __name__ 等屬性
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"⏱  {func.__name__} 執行時間：{elapsed:.4f} 秒")
        return result
    return wrapper

# ─────────────────────────────────────
# 重試裝飾器（生產環境常用）
# ─────────────────────────────────────
def retry(max_attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise  # 最後一次還是失敗，真的拋出錯誤
                    print(f"  第 {attempt+1} 次失敗：{e}，{delay}s 後重試...")
                    time.sleep(delay)
        return wrapper
    return decorator

# ─────────────────────────────────────
# 組合使用
# ─────────────────────────────────────
@timer
@retry(max_attempts=3, delay=0.5)
def fetch_data(url: str) -> dict:
    import requests
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()

# 這個函式現在：
# 1. 如果失敗，自動重試最多 3 次
# 2. 執行完後顯示耗時
```

### Context Manager：資源管理的優雅方式

```python
# ─────────────────────────────────────
# 自寫 Context Manager
# ─────────────────────────────────────
class DatabaseConnection:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connection = None
    
    def __enter__(self):
        print(f"🔗 連線到：{self.db_url}")
        self.connection = {"url": self.db_url, "active": True}
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection["active"] = False
        
        if exc_type:
            print(f"⚠️  執行中發生錯誤：{exc_val}（連線仍已關閉）")
        else:
            print("🔒 連線已正常關閉")
        
        return False  # 不壓制例外，讓它繼續往上拋

# 測試正常情況
with DatabaseConnection("postgresql://localhost/mydb") as conn:
    print(f"  連線狀態：{conn['active']}")
    # 做一些 DB 操作

# 測試例外情況
try:
    with DatabaseConnection("postgresql://localhost/mydb") as conn:
        raise ValueError("查詢語法錯誤")
except ValueError:
    print("例外已被上層捕獲")

print(f"離開後連線狀態：{conn['active']}")   # False，已關閉
```

### 課堂作業

1. 對 Lesson 7 的 `fetch_data` 套上 `@timer` + `@retry` 裝飾器
2. 故意讓 `DatabaseConnection.__exit__` 收到一個例外，確認連線還是會關閉

---

## Lesson 11：OOP + dataclass——可維護的模型設計

### 學習目標

- 用 `dataclass` 建模，`property` 計算衍生值
- 用 `Enum` 表達狀態，避免 magic string
- 能做狀態轉移的驗證

### 完整訂單模型

```python
from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from enum import Enum

class OrderStatus(Enum):
    PENDING    = "待付款"
    PAID       = "已付款"
    PROCESSING = "處理中"
    SHIPPED    = "已出貨"
    DELIVERED  = "已送達"
    CANCELLED  = "已取消"

# 合法的狀態轉移：{當前狀態: [可以轉移到的狀態]}
VALID_TRANSITIONS = {
    OrderStatus.PENDING:    [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID:       [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
    OrderStatus.PROCESSING: [OrderStatus.SHIPPED],
    OrderStatus.SHIPPED:    [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED:  [],
    OrderStatus.CANCELLED:  [],
}

@dataclass
class Product:
    id: str
    name: str
    price: float
    stock: int
    
    def is_available(self) -> bool:
        return self.stock > 0
    
    def __str__(self):
        return f"{self.name} (${self.price:,.0f}，庫存:{self.stock})"

@dataclass
class OrderItem:
    product: Product
    quantity: int
    
    @property
    def subtotal(self) -> float:
        return self.product.price * self.quantity

@dataclass
class Order:
    id: str
    customer_name: str
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self.items)
    
    def add_item(self, product: Product, quantity: int) -> bool:
        if not product.is_available():
            print(f"❌ {product.name} 已售完")
            return False
        if quantity > product.stock:
            print(f"❌ {product.name} 庫存不足（剩 {product.stock} 件）")
            return False
        
        # 已有此商品則增加數量
        for item in self.items:
            if item.product.id == product.id:
                item.quantity += quantity
                product.stock -= quantity
                return True
        
        self.items.append(OrderItem(product, quantity))
        product.stock -= quantity
        return True
    
    def transition_to(self, new_status: OrderStatus) -> bool:
        """狀態轉移，含合法性驗證"""
        allowed = VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            print(f"❌ 無法從「{self.status.value}」轉移到「{new_status.value}」")
            return False
        self.status = new_status
        print(f"✅ 訂單 {self.id} 狀態更新為：{self.status.value}")
        return True
    
    def __str__(self):
        lines = [f"訂單 #{self.id}  [{self.status.value}]  客戶：{self.customer_name}"]
        for item in self.items:
            lines.append(f"  - {item.product.name:15s} x{item.quantity:2d}  ${item.subtotal:>10,.0f}")
        lines.append(f"  {'合計':15s}       ${self.total:>10,.0f}")
        return "\n".join(lines)

# ── 測試 ──
laptop = Product("P001", "MacBook Pro", 65000, stock=5)
mouse  = Product("P002", "Magic Mouse", 2500, stock=10)

order = Order("ORD-001", "王小明")
order.add_item(laptop, 1)
order.add_item(mouse, 2)
print(order)
print()

# 合法的狀態轉移
order.transition_to(OrderStatus.PAID)
order.transition_to(OrderStatus.PROCESSING)
order.transition_to(OrderStatus.SHIPPED)

# 非法的狀態轉移
order.transition_to(OrderStatus.CANCELLED)   # 已出貨不能取消
```

---

## Lesson 11B：重構任務——把初學者程式變乾淨

### 學習目標

- 識別重複程式碼並提取成函數
- 用 dict mapping 和 dataclass 讓程式更短、更好維護

### 原始程式碼（待重構）

```python
# 這段程式「功能上正確」，但有嚴重的設計問題
# 你的任務：找出所有問題，並提出重構方案

def process_students(students):
    result = []
    for s in students:
        if s["score"] >= 90:
            r = {}
            r["name"] = s["name"]
            r["score"] = s["score"]
            r["grade"] = "A"
            result.append(r)
        elif s["score"] >= 80:
            r = {}
            r["name"] = s["name"]
            r["score"] = s["score"]
            r["grade"] = "B"
            result.append(r)
        elif s["score"] >= 70:
            r = {}
            r["name"] = s["name"]
            r["score"] = s["score"]
            r["grade"] = "C"
            result.append(r)
        else:
            r = {}
            r["name"] = s["name"]
            r["score"] = s["score"]
            r["grade"] = "F"
            result.append(r)
    return result
```

### 作業要求：交兩個版本

**版本 1：最小改動重構**（只修問題，不換架構）

```python
# 提示：
# 1. 重複的 dict 建立可以提取成什麼？
# 2. if/elif 鏈可以用什麼代替？
# 3. 函數簽名和 docstring 要補上

def get_grade(score: float) -> str:
    """根據分數回傳等第（請你實作）"""
    # 你的實作
    pass

def process_students_v1(students: list) -> list:
    """重構版本 1（請你實作）"""
    # 你的實作
    pass
```

**版本 2：進階版**（用 dataclass + 新增等第規則時不需改邏輯）

```python
from dataclasses import dataclass

@dataclass
class StudentResult:
    name: str
    score: float
    grade: str
    
    @property
    def passed(self) -> bool:
        return self.grade != "F"

# 等第規則用 list of tuple 表示，新增規則不需改函數
GRADE_RULES = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0,  "F"),  # 預設值
]

def process_students_v2(students: list) -> list[StudentResult]:
    """重構版本 2（請你實作）"""
    # 你的實作
    pass
```

### 評分重點

| 評分項目 | 說明 |
|---------|------|
| 重複碼消失 | 沒有相同邏輯寫兩次以上 |
| 可讀性 | 函數名、變數名一眼能理解意圖 |
| 擴充性 | 新增「A+ 等第（>=95）」時，V2 只改哪裡？ |
| 測試完整 | 邊界值：89.9、90、59.9、60 |

---

# Unit 5：Git 與作品集系統化 {#unit-5}

## Lesson 12：Git 核心工作流

### 學習目標

- 理解 Working Area / Staging / Repository / Remote 的差異
- 會用 `status` / `diff` / `log` 做日常操作
- 會從常見錯誤中恢復（不慌）

### 概念地圖

```
工作區（Working Directory）
    你正在編輯的檔案
        │ git add <file>
        ▼
暫存區（Staging Area）
    你決定要「記錄」的變更
        │ git commit -m "..."
        ▼
本地倉庫（Local Repository）
    你電腦上的版本歷史
        │ git push origin main
        ▼
遠端倉庫（Remote Repository）
    GitHub 上的共享版本
```

### 每天都用的指令

```bash
# === 狀態查詢 ===
git status                      # 最常用：看目前有什麼改動
git diff                        # 看未暫存的變更（工作區 vs 暫存區）
git diff --staged               # 看已暫存的變更（暫存區 vs 上次 commit）
git log --oneline --graph       # 簡潔樹狀歷史

# === 日常三步驟 ===
git add .                       # 暫存所有變更
git commit -m "feat: 新增借書功能"
git push origin main            # 推到 GitHub

# === 分支操作 ===
git branch                      # 列出所有分支
git checkout -b feature/login   # 建立並切換新分支
git merge feature/login         # 把功能分支合併到目前分支

# === 救援指令（謹慎使用！）===
git restore main.py             # ⚠️ 放棄工作區的變更（無法復原）
git restore --staged main.py    # 把檔案移出暫存區（不影響工作區）
git reset HEAD~1                # 撤銷最後一個 commit，保留變更在工作區
git stash                       # 暫時收起當前變更
git stash pop                   # 取回暫存的變更
```

### 課堂演練：故意犯錯再修復

```bash
# 演練 1：commit 後發現少了一個檔案
echo "補充說明" >> notes.md
git add notes.md
git commit --amend --no-edit   # 把 notes.md 加進上一個 commit

# 演練 2：誤改了不該改的檔案
echo "亂改的內容" >> important.py
git restore important.py        # 恢復到上次 commit 的狀態

# 演練 3：commit message 寫錯了
git commit --amend -m "fix: 修正正確的 commit message"
# ⚠️ 如果已 push 到遠端就不要用 amend（會造成歷史分叉）
```

---

## Lesson 13：Commit Message 藝術 + Repo 結構

### 學習目標

- 使用 Conventional Commits 格式寫出有意義的 message
- 建立可讀的 repo 結構

### Conventional Commits 格式

```bash
<類型>(<範圍，可選>): <簡短描述>
[空行]
[詳細說明（可選）]
[空行]
[Breaking Change / Issue 連結（可選）]
```

| 類型 | 使用時機 |
|------|---------|
| `feat` | 新增功能 |
| `fix` | 修復 bug |
| `refactor` | 重構（不改功能） |
| `docs` | 文件更新 |
| `test` | 新增或修改測試 |
| `chore` | 建置工具、套件更新 |
| `perf` | 效能優化 |
| `style` | 格式調整（空白、逗號等，不影響邏輯） |

```bash
# ❌ 壞的 commit message（對未來的你毫無意義）
git commit -m "fix"
git commit -m "update"
git commit -m "ok"
git commit -m "asdfghjkl"

# ✅ 好的 commit message
git commit -m "feat: 新增使用者 email 驗證功能"
git commit -m "fix: 修復借書時若讀者名稱含空格就崩潰的問題"
git commit -m "refactor: 將訂單金額計算邏輯提取為 OrderItem.subtotal property"
git commit -m "docs: 補充 Library.search() 的 docstring 和使用範例"
git commit -m "test: 為 get_user API 新增 404 情況的測試"
git commit -m "perf: 用 set 取代 list 做借書狀態查詢，O(n)→O(1)"
```

---

## Lesson 14：Portfolio Repo 里程碑（交付節點）

### 交付清單（必交）

| 項目 | 說明 |
|------|------|
| Repo 名稱 | `im-learning-portfolio` |
| 章節資料夾 | Unit 1–4 的成果各一個資料夾 |
| 每章 README | 學到了什麼、遇到的坑、下一步 |
| 主 README | 章節結構 + 作者 + 學習目標 |

### 建議的 README 模板

```markdown
# IM Learning Portfolio

我在資管系四年學習歷程的完整實作紀錄。

## 學習目標
- 計算思維 + 演算法基礎
- Python 工程實踐
- 資料庫與 SQL
- 系統分析與設計
- 資料分析與視覺化
- AI 整合應用

## 章節結構

| 資料夾 | 內容 | 完成度 |
|--------|------|--------|
| `ch01-computational-thinking/` | 計算思維、Big-O、Benchmark | ✅ |
| `ch02-data-structures/` | 六種結構、圖書館系統 | ✅ |
| `ch03-os-network/` | Thread、HTTP、API 呼叫 | ✅ |
| `ch04-python/` | Comprehension、Generator、Decorator、OOP | ✅ |
| `ch05-git/` | Git 工作流、Commit 規範 | ✅ |
| ... | ... | ... |
| `capstone-project/` | 期末整合專案 | 🚧 |

## 作者資訊

**姓名**：你的名字  
**學校**：你的學校  
**入學年份**：2025  
**聯絡方式**：your@email.com

## 技術棧

Python · SQLite · Flask · pandas · Git · Docker（進行中）
```

---

# Unit 6：系統設計入門 {#unit-6}

## Lesson 15：Monolith vs Microservices

### 學習目標

- 能從成本、複雜度、擴展性角度做架構選擇
- 知道「先單體，遇到痛再拆」的務實策略

### 兩種架構對比

```
單體架構（Monolith）
┌─────────────────────────────┐
│         電商平台              │
│  ┌──────┐ ┌──────┐ ┌──────┐ │
│  │ 用戶 │ │ 商品 │ │ 訂單 │ │
│  └──────┘ └──────┘ └──────┘ │
│         一個部署單元          │
└─────────────────────────────┘
優點：開發快、Debug 容易、部署簡單
缺點：難以只擴展某個模組、一個 bug 可能拖垮整個系統

微服務架構（Microservices）
┌────────┐  ┌────────┐  ┌────────┐
│ 用戶   │  │ 商品   │  │ 訂單   │
│ 服務   │  │ 服務   │  │ 服務   │
└───┬────┘  └───┬────┘  └───┬────┘
    └──────────┬┘────────────┘
           API Gateway / 訊息佇列
優點：可獨立擴展、故障隔離、技術棧可混用
缺點：運維複雜、服務間通訊要處理、分散式問題難 Debug
```

### 架構選擇決策

```
你的系統是：
│
├─ 早期新創 / 小型系統 / 不確定需求
│  → 先用單體架構
│  → 等到確定哪個模組需要獨立擴展再拆
│
├─ 有明確獨立擴展需求
│  （如：商品搜尋流量是訂單的 100 倍）
│  → 考慮把搜尋服務單獨拆出來
│
└─ 大型組織 / 多團隊並行開發
   → 微服務讓各團隊獨立部署，降低協調成本
```

### 課堂討論題

分組，每組選一個情境，說明選哪種架構、理由是什麼：

| 情境 | 選單體還是微服務？為什麼？ |
|------|--------------------------|
| 系學會的選課系統（100 個用戶） | |
| 課堂媒合平台新創（5 人團隊，MVP 階段） | |
| 台灣大型電商（每天 100 萬訂單） | |

---

## Lesson 16：Cache 與 Load Balancer——高可用基礎

### 學習目標

- 知道快取命中/失效/TTL 的概念與風險
- 了解負載平衡策略的差異

### Cache 的核心概念

```python
import functools
import time

def simple_cache(ttl_seconds: int = 60):
    """
    記憶體快取裝飾器
    
    問題：快取的三大風險
    1. 髒資料：資料更新了但快取沒更新
    2. 快取穿透：查不存在的資料，每次都打到 DB
    3. 快取雪崩：大量快取同時過期，DB 被打爆
    """
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args):
            key = str(args)
            now = time.time()
            
            if key in cache and now - cache[key]["time"] < ttl_seconds:
                print(f"  ⚡ [快取命中] {func.__name__}({args})")
                return cache[key]["value"]
            
            print(f"  🔄 [快取失效] {func.__name__}({args})，查詢 DB...")
            result = func(*args)
            cache[key] = {"value": result, "time": now}
            return result
        
        def invalidate(key_args=None):
            """主動清除快取（資料更新時呼叫）"""
            if key_args:
                cache.pop(str(key_args), None)
            else:
                cache.clear()
        
        wrapper.invalidate = invalidate
        return wrapper
    return decorator

# 模擬慢查詢
@simple_cache(ttl_seconds=5)
def get_product(product_id: str) -> dict:
    time.sleep(0.3)   # 模擬 DB 查詢
    return {"id": product_id, "name": f"商品{product_id}", "price": 999}

# 測試
print("=== 第一次查詢（DB） ===")
start = time.time()
p = get_product("P001")
print(f"  耗時：{time.time()-start:.2f} 秒")

print("\n=== 第二次查詢（快取） ===")
start = time.time()
p = get_product("P001")
print(f"  耗時：{time.time()-start:.4f} 秒")
```

### 反思題（請寫進 README）

1. 如果商品價格改了，你的快取怎麼失效？
2. 什麼是「快取穿透」？怎麼防止有人用不存在的 ID 打爆你的 DB？

### 負載平衡的三種策略

```
             用戶請求
                │
       ┌────────┴────────┐
       │   Load Balancer  │
       └────────┬─────────┘
    ┌──────────┬┘─────────────┐
    ▼          ▼              ▼
┌────────┐ ┌────────┐    ┌────────┐
│ 伺服器1 │ │ 伺服器2 │    │ 伺服器3 │
└────────┘ └────────┘    └────────┘

Round Robin（輪詢）：
  1→2→3→1→2→3...
  優點：簡單；缺點：不考慮伺服器負載

Least Connections（最少連線）：
  送給目前連線最少的伺服器
  優點：自動避開忙碌的伺服器

IP Hash（IP 雜湊）：
  同一個 IP 固定送到同一台伺服器
  優點：Session 一致性；缺點：負載可能不均
```

---

## Lesson 17：設計題——短網址服務

### 學習目標

- 練習「從需求推架構」的思考流程
- 完成一個完整的小型設計 + 簡化實作

### 設計問題（先自己想，再看參考）

```
需求：
- 輸入長 URL → 得到短 URL（如 http://short.ly/abc123）
- 點擊短 URL → 重新導向到原始 URL
- 每天 1 億次點擊

請回答：
1. 你用什麼資料庫存 URL 對應關係？為什麼？
2. 短碼（abc123）怎麼生成？如何確保不重複？
3. 支援 1 億次點擊的最大瓶頸是什麼？
4. 畫出系統架構圖（文字版即可）
```

**參考答案（想清楚再看）**

```
1. 資料庫選型：
   - 讀多寫少（查詢 >> 新增）→ 最適合 key-value 或 cache
   - 主儲存用 PostgreSQL（保證 ACID）
   - 高頻讀取用 Redis 快取（TTL = 熱門 URL 一天）

2. 短碼生成策略：
   - 方案 A：hash(original_url) 取前 6 字元（有碰撞風險）
   - 方案 B：全局自增 ID 轉 Base62
     → ID=12345 → "dnh" （62 進位，6 碼可表達 568 億個 URL）
   - 碰撞處理：insert 失敗就重試（B 方案不會碰撞）

3. 瓶頸：
   - 讀取（展開短網址）是主要瓶頸
   - 解法：Redis 快取 + CDN + 讀寫分離 DB

4. 架構圖：
   [用戶] → [CDN / Edge Cache] → [API Server] → [Redis Cache]
                                       │                │（miss）
                                    [DB Read Replica] ←─┘
```

### 簡化實作

```python
import hashlib
import base64
import sqlite3
from datetime import datetime
from contextlib import contextmanager

class URLShortener:
    def __init__(self, db_path: str = "urls.db"):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS urls (
                    short_code  TEXT PRIMARY KEY,
                    original    TEXT NOT NULL,
                    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                    click_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_original ON urls(original)")
    
    def _generate_code(self, url: str) -> str:
        return base64.urlsafe_b64encode(
            hashlib.sha256(url.encode()).digest()
        )[:6].decode()
    
    def shorten(self, original_url: str) -> str:
        with self._get_conn() as conn:
            # 先查是否已有此 URL
            row = conn.execute(
                "SELECT short_code FROM urls WHERE original = ?", (original_url,)
            ).fetchone()
            if row:
                return f"http://short.ly/{row['short_code']}"
            
            code = self._generate_code(original_url)
            conn.execute(
                "INSERT INTO urls (short_code, original) VALUES (?, ?)",
                (code, original_url)
            )
        return f"http://short.ly/{code}"
    
    def expand(self, short_code: str) -> str | None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE urls SET click_count = click_count + 1 WHERE short_code = ?",
                (short_code,)
            )
            row = conn.execute(
                "SELECT original FROM urls WHERE short_code = ?", (short_code,)
            ).fetchone()
        return row["original"] if row else None
    
    def stats(self, short_code: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM urls WHERE short_code = ?", (short_code,)
            ).fetchone()
        return dict(row) if row else None

# ── 測試 ──
svc = URLShortener()
long_url = "https://www.example.com/very/long/path?param1=value1&param2=value2"
short = svc.shorten(long_url)
print(f"短網址：{short}")

code = short.split("/")[-1]
print(f"展開：{svc.expand(code)}")
print(f"統計：{svc.stats(code)}")
```

### 交付內容

1. `design_questions.md`：回答 4 個設計問題 + 架構圖
2. `url_shortener.py`：完整實作，含測試

### 評分規準（滿分 15 分）

| 項目 | 分數 |
|------|------|
| 4 個設計問題都有合理回答 | 6 |
| 短碼碰撞如何處理（至少提出策略） | 2 |
| 知道讀取是主要瓶頸並提出解法 | 2 |
| 架構圖合理（文字圖也算） | 2 |
| 程式碼可運作，有 context manager | 3 |

---

# Unit 7：關聯式資料庫與 SQL {#unit-7}

## Lesson 18：ERD 與正規化（3NF）

### 學習目標

- 能把情境轉成實體、關係、外鍵
- 理解為什麼要拆成多張表（正規化的動機）
- 知道 `order_items` 是如何解決 M:N 關係的

### 電商系統 ER 圖

```
[客戶]                [訂單]               [訂單明細]            [商品]
customer_id ─── 1:N ─ order_id ─── 1:N ─── item_id  ─── N:1 ─── product_id
name                  customer_id           order_id             name
email                 created_at            product_id           price
                      status                quantity             stock
                                            unit_price（下單當時的價格）

重點：
  一個客戶可以有多個訂單（1:N）
  一個訂單可以有多個商品（M:N，透過 order_items 解決）
  unit_price 存在 order_items 而非 products，是因為商品可以改價
```

### 從壞設計看正規化的必要

```sql
-- ❌ 未正規化：資料重複、更新異常
CREATE TABLE bad_orders (
    order_id      INTEGER,
    customer_name VARCHAR(50),       -- 同一個客戶多次重複
    customer_email VARCHAR(100),
    product_name  VARCHAR(100),
    product_price DECIMAL(10,2),     -- 商品改價後舊訂單怎麼辦？
    quantity      INTEGER
);
-- 問題 1：客戶改 email → 要更新所有相關訂單
-- 問題 2：商品下架 → 要查多少筆才能確認是否還在用？
-- 問題 3：同一筆訂單有多個商品 → 要複製訂單基本資料幾次？

-- ✅ 正規化後（第三正規化，3NF）
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL
);
CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    price       REAL NOT NULL CHECK (price > 0),
    stock       INTEGER DEFAULT 0 CHECK (stock >= 0)
);
CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    status      TEXT DEFAULT 'pending',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
CREATE TABLE order_items (
    item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  REAL NOT NULL,   -- 存下單當時的價格（不受商品改價影響）
    FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
```

### 課堂實作

1. 用文字方塊（或 Mermaid）畫出 ER 圖
2. 把 `bad_orders` 轉換成 3NF 的四張表
3. 提交 `ch07-database-sql/schema.sql`

---

## Lesson 19：SQL 基礎到 JOIN 聚合

### 學習目標

- 熟練 `SELECT / WHERE / ORDER / LIMIT / LIKE / JOIN`
- 能寫出 `GROUP BY + HAVING` 的分析查詢

### 測試資料建立

```sql
-- 先插入一些測試資料
INSERT INTO customers (name, email) VALUES 
    ('王小明', 'wang@test.com'),
    ('李小花', 'lee@test.com'),
    ('張大偉', 'zhang@test.com');

INSERT INTO products (name, price, stock) VALUES
    ('MacBook Pro', 65000, 5),
    ('AirPods Pro', 8000, 20),
    ('iPhone 15',   32000, 15);
```

### 基礎查詢

```sql
-- 基本選取
SELECT name, email FROM customers;

-- WHERE 過濾
SELECT name, price FROM products WHERE price > 10000;

-- ORDER BY 排序（預設 ASC，降序用 DESC）
SELECT name, price FROM products ORDER BY price DESC;

-- LIMIT 分頁（第 2 頁，每頁 10 筆）
SELECT * FROM products ORDER BY product_id LIMIT 10 OFFSET 10;

-- LIKE 模糊搜尋（% = 任意字元）
SELECT * FROM products WHERE name LIKE '%Pro%';

-- COUNT / AVG / SUM / MAX / MIN
SELECT 
    COUNT(*) AS 商品總數,
    AVG(price) AS 平均售價,
    MAX(price) AS 最高售價,
    MIN(price) AS 最低售價
FROM products;
```

### JOIN 查詢

```sql
-- INNER JOIN：只回傳兩邊都有對應資料的行
SELECT 
    c.name AS 客戶姓名,
    o.order_id,
    o.status,
    o.created_at
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
ORDER BY o.created_at DESC;

-- 三表 JOIN：客戶、訂單、商品
SELECT 
    c.name AS 客戶,
    p.name AS 商品,
    oi.quantity AS 數量,
    oi.unit_price AS 單價,
    (oi.quantity * oi.unit_price) AS 小計
FROM customers c
JOIN orders o      ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p    ON oi.product_id = p.product_id
WHERE o.status = 'completed'
ORDER BY c.name, 小計 DESC;
```

### GROUP BY + HAVING 分析查詢

```sql
-- 每個客戶的消費總額（含未下訂的客戶）
SELECT 
    c.name AS 客戶姓名,
    COUNT(DISTINCT o.order_id) AS 訂單數,
    COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS 消費總額,
    MAX(o.created_at) AS 最近訂購日
FROM customers c
LEFT JOIN orders o       ON c.customer_id = o.customer_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.name
ORDER BY 消費總額 DESC;

-- HAVING：只顯示消費超過 10,000 的客戶
-- （WHERE 過濾行，HAVING 過濾群組）
SELECT 
    c.name,
    SUM(oi.quantity * oi.unit_price) AS total
FROM customers c
JOIN orders o       ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.name
HAVING total > 10000
ORDER BY total DESC;
```

### 課後作業

1. 自己新增 20 筆測試訂單資料
2. 跑「客戶消費排行」查詢並截圖貼到 README
3. 寫一個查詢：找出**庫存少於 5 件且至少有 1 筆訂單**的商品

---

## Lesson 20：Window Functions + Index + Explain

### 學習目標

- 用 RANK / LAG / NTILE 做進階排名與趨勢分析
- 理解索引的作用與建立時機

### 視窗函數

```sql
-- 計算每個客戶的消費排名（全體排名）
SELECT 
    c.name,
    SUM(oi.quantity * oi.unit_price) AS total_spending,
    RANK() OVER (
        ORDER BY SUM(oi.quantity * oi.unit_price) DESC
    ) AS spending_rank,
    NTILE(4) OVER (
        ORDER BY SUM(oi.quantity * oi.unit_price) DESC
    ) AS quartile   -- 前 25% 是 Q1，後 25% 是 Q4
FROM customers c
JOIN orders o       ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.name;

-- 月度收入 + 前月比較（LAG）
WITH monthly AS (
    SELECT 
        strftime('%Y-%m', o.created_at) AS month,
        SUM(oi.quantity * oi.unit_price) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY month
)
SELECT 
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY month)) /
        LAG(revenue) OVER (ORDER BY month) * 100, 1
    ) AS growth_pct
FROM monthly
ORDER BY month;
```

### 索引——讓查詢快 100 倍

```sql
-- 問題：每次查某客戶的訂單都要掃全表
EXPLAIN QUERY PLAN
SELECT * FROM orders WHERE customer_id = 1;
-- 結果：SCAN TABLE orders（O(n)，逐行掃描）

-- 解法：建立索引
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_items_order     ON order_items(order_id);

-- 建立後再查
EXPLAIN QUERY PLAN
SELECT * FROM orders WHERE customer_id = 1;
-- 結果：SEARCH TABLE orders USING INDEX idx_orders_customer（O(log n)）

-- 複合索引（常一起查詢的欄位）
CREATE INDEX idx_orders_status_date ON orders(status, created_at);
```

**索引的代價**：每次 INSERT / UPDATE / DELETE 都要維護索引 → 寫入變慢。
建立索引前問自己：**這個欄位是不是 WHERE 或 JOIN ON 的常用條件？**

---

## Lesson 21：Python 操作 SQLite（交易一致性）

### 學習目標

- 理解 transaction 的必要性（庫存扣除 + 訂單建立必須一致）
- 能用 contextmanager 做 commit / rollback

### 完整實作

```python
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional

class EcommerceDB:
    def __init__(self, db_path: str = "ecommerce.db"):
        self.db_path = db_path
        self._init_schema()
    
    @contextmanager
    def get_conn(self):
        """Context manager：確保 commit/rollback + 關閉連線"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        with self.get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                );
                CREATE TABLE IF NOT EXISTS products (
                    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    stock INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                );
                CREATE TABLE IF NOT EXISTS order_items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id),
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                );
                CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
                CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);
            """)
    
    def create_order(self, customer_id: int, items: List[Dict]) -> int:
        """
        建立訂單（在同一個交易中完成庫存扣除 + 明細新增）
        
        若任何步驟失敗，整個交易 rollback，庫存不會被錯誤扣除。
        
        Args:
            items: [{"product_id": 1, "quantity": 2}, ...]
        Returns:
            新訂單的 order_id
        """
        with self.get_conn() as conn:
            # Step 1：驗證所有商品的庫存
            for item in items:
                row = conn.execute(
                    "SELECT name, stock FROM products WHERE product_id = ?",
                    (item["product_id"],)
                ).fetchone()
                
                if not row:
                    raise ValueError(f"商品 {item['product_id']} 不存在")
                if row["stock"] < item["quantity"]:
                    raise ValueError(
                        f"商品《{row['name']}》庫存不足"
                        f"（需要 {item['quantity']}，剩餘 {row['stock']}）"
                    )
            
            # Step 2：建立訂單
            cursor = conn.execute(
                "INSERT INTO orders (customer_id) VALUES (?)", (customer_id,)
            )
            order_id = cursor.lastrowid
            
            # Step 3：新增明細 + 扣庫存
            for item in items:
                price = conn.execute(
                    "SELECT price FROM products WHERE product_id = ?",
                    (item["product_id"],)
                ).fetchone()["price"]
                
                conn.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
                    (order_id, item["product_id"], item["quantity"], price)
                )
                conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE product_id = ?",
                    (item["quantity"], item["product_id"])
                )
            
            return order_id
    
    def get_customer_analytics(self) -> List[Dict]:
        """客戶消費分析報表"""
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT 
                    c.name,
                    COUNT(DISTINCT o.order_id) AS order_count,
                    COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_spent,
                    MAX(o.created_at) AS last_order_date
                FROM customers c
                LEFT JOIN orders o       ON c.customer_id = o.customer_id
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                GROUP BY c.customer_id, c.name
                ORDER BY total_spent DESC
            """).fetchall()
            return [dict(r) for r in rows]

# ── 測試：驗證 rollback 機制 ──
db = EcommerceDB()

with db.get_conn() as conn:
    conn.execute("INSERT OR IGNORE INTO customers (name, email) VALUES ('王小明', 'wang@test.com')")
    conn.execute("INSERT OR IGNORE INTO products (name, price, stock) VALUES ('MacBook', 65000, 2)")
    conn.execute("INSERT OR IGNORE INTO products (name, price, stock) VALUES ('AirPods', 8000, 10)")

# 正常訂單
try:
    oid = db.create_order(1, [{"product_id": 1, "quantity": 1}])
    print(f"✅ 訂單 #{oid} 建立成功")
except ValueError as e:
    print(f"❌ {e}")

# 庫存不足（應該 rollback，兩個商品的庫存都不變）
try:
    oid = db.create_order(1, [
        {"product_id": 1, "quantity": 5},   # 超過庫存！
        {"product_id": 2, "quantity": 1}
    ])
except ValueError as e:
    print(f"❌ 預期錯誤：{e}")
    print("   ← AirPods 的庫存應該沒被扣除")
```

---

# Unit 8：資料分析與視覺化 {#unit-8}

## Lesson 22：pandas EDA（探索性資料分析）

### 學習目標

- 用 `info / describe / value_counts / groupby` 做基礎探索
- 知道時間欄位的處理方式

### 生成測試資料 + 基礎 EDA

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

np.random.seed(42)
N = 1000

products = ['MacBook', 'iPhone', 'AirPods', 'iPad', 'Watch']
categories = {'MacBook':'電腦','iPhone':'手機','AirPods':'配件','iPad':'平板','Watch':'配件'}
prices = {'MacBook':65000,'iPhone':32000,'AirPods':8000,'iPad':25000,'Watch':12000}

df = pd.DataFrame({
    'date': [datetime(2024,1,1)+timedelta(days=random.randint(0,364)) for _ in range(N)],
    'product': [random.choice(products) for _ in range(N)],
    'quantity': np.random.randint(1, 5, N),
    'region': [random.choice(['北部','中部','南部','東部']) for _ in range(N)]
})
df['category'] = df['product'].map(categories)
df['unit_price'] = df['product'].map(prices)
df['revenue'] = df['quantity'] * df['unit_price']
df['date'] = pd.to_datetime(df['date'])
df['month'] = df['date'].dt.to_period('M')

# ── EDA 三步驟 ──
print("【1】資料基本資訊")
print(df.info())
print(df.describe())

print("\n【2】分佈探索")
print(df['product'].value_counts())
print(df.groupby('region')['revenue'].sum().sort_values(ascending=False))

print("\n【3】至少找出 3 個洞察")
# 例：哪個地區的平均客單價最高？
avg_order = df.groupby('region').agg(
    avg_revenue=('revenue','mean'),
    total_revenue=('revenue','sum'),
    order_count=('revenue','count')
).round(0)
print(avg_order)
```

### 課後作業（3 個洞察）

用 EDA 結果，在 `report.md` 寫出：

```markdown
## 銷售資料探索報告

### 洞察 1：XXX
- 觀察：...（數字支撐）
- 建議：...

### 洞察 2：XXX
...

### 洞察 3：XXX
...
```

---

## Lesson 23：RFM 客戶分群

### 學習目標

- 能產出 RFM 表格並正確解讀分數
- 能為每個客群提出具體策略

### RFM 分析完整流程

```python
df['customer_id'] = np.random.randint(1, 201, N)
reference_date = pd.Timestamp('2025-01-01')

rfm = df.groupby('customer_id').agg(
    recency=('date', lambda x: (reference_date - x.max()).days),
    frequency=('date', 'count'),
    monetary=('revenue', 'sum')
).reset_index()

# 分數：5 分最好，1 分最差
rfm['R'] = pd.qcut(rfm['recency'],  5, labels=[5,4,3,2,1])  # 越近越好
rfm['F'] = pd.qcut(rfm['frequency'], 5, labels=[1,2,3,4,5], duplicates='drop')
rfm['M'] = pd.qcut(rfm['monetary'],  5, labels=[1,2,3,4,5], duplicates='drop')
rfm['RFM'] = rfm['R'].astype(int) + rfm['F'].astype(int) + rfm['M'].astype(int)

SEGMENTS = [
    (13, '💎 VIP 客戶',   '個人化優惠、搶先體驗新品'),
    (10, '⭐ 重要客戶',   '升等計畫、生日禮'),
    ( 7, '🔄 一般客戶',   '定期推播、促銷活動'),
    ( 0, '😴 流失風險',   '喚回優惠、問卷了解原因'),
]

def classify(score):
    for threshold, label, _ in SEGMENTS:
        if score >= threshold:
            return label
    return SEGMENTS[-1][1]

rfm['segment'] = rfm['RFM'].apply(classify)

print("客戶分層結果：")
print(rfm.groupby('segment').agg(
    客戶數=('customer_id','count'),
    平均消費=('monetary','mean'),
    平均購買次數=('frequency','mean')
).round(0))
```

### 作業（必交）

為每個客群各寫一個具體的行銷 / 產品策略：

| 客群 | 策略 | 預期效果 |
|------|------|---------|
| 💎 VIP 客戶 | | |
| ⭐ 重要客戶 | | |
| 🔄 一般客戶 | | |
| 😴 流失風險 | | |

---

## Lesson 24：視覺化儀表板 + 報告寫作

### 學習目標

- 做 2–4 張支撐結論的圖表
- 學會「結論 → 證據 → 建議」的報告結構

### 四格儀表板

```python
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = ['sans-serif']

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('電商銷售分析儀表板', fontsize=16, fontweight='bold')

# 1. 月度收入趨勢
monthly = df.groupby('month')['revenue'].sum().reset_index()
monthly['month'] = monthly['month'].dt.to_timestamp()
ax = axes[0, 0]
ax.plot(monthly['month'], monthly['revenue']/1000, marker='o', linewidth=2, color='steelblue')
ax.set_title('月度收入趨勢（千元）')
ax.tick_params(axis='x', rotation=45)
ax.grid(True, alpha=0.3)

# 2. 商品收入佔比
ax = axes[0, 1]
prod_rev = df.groupby('product')['revenue'].sum()
ax.pie(prod_rev, labels=prod_rev.index, autopct='%1.1f%%', startangle=90)
ax.set_title('商品收入佔比')

# 3. 地區 x 類別堆疊長條
ax = axes[1, 0]
pivot = df.groupby(['region','category'])['revenue'].sum().unstack(fill_value=0)
pivot.div(1000).plot(kind='bar', stacked=True, ax=ax, colormap='viridis')
ax.set_title('各地區類別收入（千元）')
ax.legend(bbox_to_anchor=(1.05, 1))
ax.tick_params(axis='x', rotation=0)

# 4. 每週各天收入箱型圖
ax = axes[1, 1]
df['dow'] = df['date'].dt.day_name()
day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
df_dow = df.copy()
df_dow['dow'] = pd.Categorical(df_dow['dow'], categories=day_order, ordered=True)
df_dow.boxplot(column='revenue', by='dow', ax=ax)
ax.set_title('每週各天收入分布')
ax.set_xlabel('')
plt.xticks(rotation=30)

plt.tight_layout()
plt.savefig('sales_dashboard.png', dpi=150, bbox_inches='tight')
print("✅ 儀表板已儲存為 sales_dashboard.png")
```

### 報告模板（`report.md`）

```markdown
# 2024 電商銷售分析報告

## 執行摘要
（2 句話：最重要的發現 + 最重要的建議）

## 月度收入趨勢
![月度趨勢](sales_dashboard.png)

**發現**：Q4 收入比 Q1 高 XX%，11 月有明顯高峰。
**建議**：提前 2 個月準備 Q4 庫存，尤其是 MacBook 和 iPhone。

## 客戶分群洞察
...

## 商品表現
...

## 建議優先事項
1. 高優先：...
2. 中優先：...
3. 長期：...
```

---

# Unit 9：NoSQL 選型與快取思維 {#unit-9}

## Lesson 25：什麼時候不用 SQL

### 選型速查表

| 需求情境 | 推薦技術 | 代表產品 |
|---------|---------|---------|
| 彈性結構（每筆資料欄位不同） | 文件型 | MongoDB |
| 極快 key-value 查詢、快取、Session | 鍵值型 | Redis |
| 複雜關係查詢（社交網路、推薦） | 圖形型 | Neo4j |
| 大量時序資料（IoT、日誌） | 時序型 | InfluxDB |
| 結構固定、ACID 需求 | 關聯式 | PostgreSQL |

**何時用 MongoDB？**
- 商品規格不統一（手機有顏色/記憶體，書有 ISBN/作者）
- 需要快速迭代 schema，不想每次都 ALTER TABLE

**何時用 Redis？**
- 快取（減少 DB 查詢）
- Session 管理（用戶登入狀態）
- 速率限制（API rate limiting）
- 排行榜（利用 Sorted Set）

---

## Lesson 26：Redis 三大用法（Mock 版本練習）

### 完整實作（含 Mock Redis）

```python
import json
import time
from typing import Any, Optional

class MockRedis:
    """模擬 Redis 基本功能（教學用途，非生產）"""
    def __init__(self):
        self._store = {}
        self._expiry = {}
    
    def set(self, key: str, value: str, ex: int = None) -> bool:
        self._store[key] = value
        if ex:
            self._expiry[key] = time.time() + ex
        return True
    
    def get(self, key: str) -> Optional[str]:
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._store[key], self._expiry[key]
            return None
        return self._store.get(key)
    
    def delete(self, key: str) -> int:
        deleted = key in self._store
        self._store.pop(key, None)
        self._expiry.pop(key, None)
        return int(deleted)
    
    def incr(self, key: str) -> int:
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = str(val)
        return val

redis = MockRedis()

# ─────────────────────────────────────
# 用法 1：查詢結果快取
# ─────────────────────────────────────
def get_product_cached(product_id: str, db_query_fn) -> dict:
    key = f"product:{product_id}"
    cached = redis.get(key)
    
    if cached:
        print(f"  ⚡ Cache HIT: {key}")
        return json.loads(cached)
    
    print(f"  🔄 Cache MISS: {key}，查詢 DB...")
    product = db_query_fn(product_id)
    redis.set(key, json.dumps(product), ex=600)  # 快取 10 分鐘
    return product

# ─────────────────────────────────────
# 用法 2：Session 管理
# ─────────────────────────────────────
import uuid

class SessionManager:
    TTL = 3600  # 1 小時
    
    def create(self, user_id: int, user_data: dict) -> str:
        sid = str(uuid.uuid4())
        redis.set(
            f"session:{sid}",
            json.dumps({"user_id": user_id, **user_data}),
            ex=self.TTL
        )
        return sid
    
    def get(self, session_id: str) -> Optional[dict]:
        raw = redis.get(f"session:{session_id}")
        return json.loads(raw) if raw else None
    
    def destroy(self, session_id: str) -> bool:
        return bool(redis.delete(f"session:{session_id}"))

# ─────────────────────────────────────
# 用法 3：API 速率限制（Rate Limiting）
# ─────────────────────────────────────
class RateLimiter:
    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max = max_requests
        self.window = window
    
    def is_allowed(self, client_ip: str) -> tuple[bool, int]:
        """
        Returns: (是否允許, 目前計數)
        """
        key = f"rate:{client_ip}"
        count = redis.incr(key)
        
        if count == 1:
            redis.set(key, "1", ex=self.window)   # 第一次設定 TTL
        
        remaining = max(0, self.max - count)
        allowed = count <= self.max
        
        if not allowed:
            print(f"  🚫 {client_ip} 已超過限制 ({count}/{self.max})")
        
        return allowed, remaining

# ── 測試 ──
sessions = SessionManager()
sid = sessions.create(123, {"name": "王小明", "role": "user"})
print(f"Session: {sessions.get(sid)}")

limiter = RateLimiter(max_requests=3, window=60)
for i in range(5):
    ok, rem = limiter.is_allowed("192.168.1.1")
    print(f"請求 {i+1}: {'✅' if ok else '❌'}, 剩餘 {rem} 次")
```

### 課後作業（加分）

自己設計一個「短網址點擊數快取 + 批次回寫」機制：

1. 每次點擊 → 在 Redis 累計計數（不立即寫 DB）
2. 每 100 次或每 5 分鐘 → 把計數批次寫回 SQLite
3. 說明：這樣設計的好處與風險是什麼？

---

# Unit 10：系統分析與資安基礎 {#unit-10}

## Lesson 27：UML——Use Case + Sequence

### 課堂實作：為圖書館系統畫圖

```
【Use Case 圖】

        ╔═════════════════════════════════╗
        ║          圖書館管理系統           ║
        ║                                 ║
讀者 ──►║  ○ 搜尋書籍                    ║
        ║  ○ 借書                         ║
        ║  ○ 還書                         ║
        ║  ○ 查看借閱記錄                 ║
        ║                                 ║
館員 ──►║  ○ 新增書籍                    ║
        ║  ○ 查看逾期未還清單              ║
        ║  ○ 系統設定                     ║
        ╚═════════════════════════════════╝

【Sequence 圖：借書流程】

讀者         前端          系統           資料庫
  │           │              │               │
  │ 輸入書號  │              │               │
  ├──────────►│              │               │
  │           │ borrow(id)   │               │
  │           ├─────────────►│               │
  │           │              │ 查書況 + 借閱記錄│
  │           │              ├──────────────►│
  │           │              │ {可借，無逾期} │
  │           │              │◄──────────────┤
  │           │              │ 更新借閱記錄   │
  │           │              ├──────────────►│
  │           │              │    OK         │
  │           │              │◄──────────────┤
  │           │  {success}   │               │
  │           │◄─────────────┤               │
  │ 顯示成功  │              │               │
  │◄──────────┤              │               │
```

---

## Lesson 28：RESTful API 設計規範

### 完整 Flask 實作

```python
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

# ── 統一回應格式 ──
def ok(data, code=200):
    return jsonify({"success": True, "data": data}), code

def err(msg, code=400):
    return jsonify({"success": False, "error": {"message": msg, "code": code}}), code

# ── 認證裝飾器 ──
def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return err("請提供 Authorization header", 401)
        # 真實系統：驗證 JWT token
        return f(*args, **kwargs)
    return wrapper

# ── 商品 API ──

# GET  /products          列出商品（支援分頁、類別篩選）
# GET  /products/{id}     取得單一商品
# POST /products          新增商品（需認證）
# PATCH /products/{id}   更新商品（需認證）
# DELETE /products/{id}  刪除商品（需認證）

MOCK_PRODUCTS = [
    {"id": 1, "name": "MacBook Pro", "price": 65000, "category": "電腦"},
    {"id": 2, "name": "iPhone 15",   "price": 32000, "category": "手機"},
    {"id": 3, "name": "AirPods Pro", "price":  8000, "category": "配件"},
]

@app.route('/products', methods=['GET'])
def list_products():
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category')
    
    products = MOCK_PRODUCTS
    if category:
        products = [p for p in products if p['category'] == category]
    
    start = (page - 1) * per_page
    return ok({
        "products": products[start:start+per_page],
        "pagination": {
            "page": page, "per_page": per_page,
            "total": len(products),
            "total_pages": (len(products) + per_page - 1) // per_page
        }
    })

@app.route('/products/<int:pid>', methods=['GET'])
def get_product(pid):
    p = next((p for p in MOCK_PRODUCTS if p['id'] == pid), None)
    return ok(p) if p else err(f"商品 {pid} 不存在", 404)

@app.route('/products', methods=['POST'])
@require_auth
def create_product():
    data = request.get_json() or {}
    missing = [f for f in ['name', 'price'] if f not in data]
    if missing:
        return err(f"缺少必填欄位：{', '.join(missing)}", 400)
    if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
        return err("price 必須是正數", 400)
    
    new_p = {"id": max(p['id'] for p in MOCK_PRODUCTS) + 1, **data}
    MOCK_PRODUCTS.append(new_p)
    return ok(new_p, 201)

@app.route('/products/<int:pid>', methods=['DELETE'])
@require_auth
def delete_product(pid):
    global MOCK_PRODUCTS
    MOCK_PRODUCTS = [p for p in MOCK_PRODUCTS if p['id'] != pid]
    return '', 204

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

---

## Lesson 29：資安基礎（OWASP 開發者版本）

### 四大必知漏洞

**1. SQL Injection**

```python
import sqlite3

# ❌ 危險：字串拼接 SQL
def login_vulnerable(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pw='{password}'"
    # 攻擊者輸入 username = "admin' --"
    # 實際執行：SELECT * FROM users WHERE name='admin' --' AND pw='...'
    # -- 是 SQL 註解，密碼驗證被跳過！

# ✅ 安全：參數化查詢
def login_safe(username, password):
    conn = sqlite3.connect("users.db")
    return conn.execute(
        "SELECT * FROM users WHERE name = ? AND pw = ?",
        (username, password)
    ).fetchone()
```

**2. 密碼儲存（永遠不要存明文）**

```python
import bcrypt   # pip install bcrypt

def hash_password(password: str) -> bytes:
    """bcrypt 自動生成 salt，抗彩虹表攻擊"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)

# 測試
pw = "MySecretPassword123!"
hashed = hash_password(pw)
print(f"儲存的 hash：{hashed[:30]}...")
print(f"驗證正確密碼：{verify_password(pw, hashed)}")       # True
print(f"驗證錯誤密碼：{verify_password('wrong', hashed)}")  # False
```

**3. JWT 認證**

```python
import jwt, secrets, datetime

SECRET = secrets.token_hex(32)  # 真實環境從環境變數讀取，不要寫死在程式碼！

def create_token(user_id: int, role: str) -> str:
    return jwt.encode({
        "sub": str(user_id),
        "role": role,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET, algorithm="HS256")

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token 已過期，請重新登入")
    except jwt.InvalidTokenError:
        raise ValueError("Token 無效或被竄改")

token = create_token(123, "admin")
payload = verify_token(token)
print(f"user_id={payload['sub']}, role={payload['role']}")
```

**4. 輸入驗證**

```python
import re

class Validator:
    @staticmethod
    def email(v: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v))
    
    @staticmethod
    def phone_tw(v: str) -> bool:
        return bool(re.match(r'^09\d{8}$', v.replace('-','').replace(' ','')))
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """防止 XSS：轉義 HTML 特殊字元（生產環境用 bleach 套件）"""
        return text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
```

### 作業：提交四個小檔

| 檔案 | 內容 |
|------|------|
| `sqli_demo.py` | 示範危險寫法 vs 參數化查詢 |
| `password_hashing.py` | bcrypt hash + verify |
| `jwt_demo.py` | create + verify token |
| `input_validation.py` | email / phone / html 驗證 |

README 格式：

```markdown
## 資安練習筆記

| 風險 | 錯誤示範 | 正確做法 |
|------|---------|---------|
| SQL Injection | 字串拼接 SQL | 參數化查詢（? 佔位符） |
| 密碼洩露 | 明文或 MD5 | bcrypt + salt（rounds=12） |
| Token 偽造 | 無簽名 | JWT HS256 + exp |
| XSS | 直接顯示輸入 | 轉義 HTML + sanitize |
```

---

# Unit 11：敏捷開發與專案管理 {#unit-11}

## Lesson 30：Agile vs Waterfall + Scrum

### 瀑布式 vs 敏捷

```
瀑布式（Waterfall）：
需求分析(3月) → 系統設計(2月) → 開發(6月) → 測試(2月) → 上線
問題：一年後才知道做的是不是用戶要的東西。

敏捷式（Scrum）：
每個 Sprint（2週）都交付可運作的小功能
→ 2週後就能拿到用戶反饋 → 早期修正方向
```

### Scrum 三角色 + 五流程

```
三角色：
  Product Owner (PO)  → 代表業務方，決定做什麼、優先順序
  Scrum Master (SM)   → 流程守護者，移除障礙
  Development Team    → 實際完成工作的人（3–9 人）

五流程（每個 Sprint）：
  1. Sprint Planning   → 決定這個 Sprint 要做哪些 backlog items
  2. Daily Standup     → 15 分鐘：昨天做了什麼？今天要做什麼？有什麼阻礙？
  3. Sprint Review     → 展示成果給 PO + 利害關係人
  4. Sprint Retro      → 反思：哪些做得好？哪些要改進？
  （Sprint Backlog Refinement 穿插在中間）
```

### 課堂活動：Sprint Planning 演練

分組，針對期末專案做一次 Sprint Planning：

1. 把期末專案拆成至少 10 個 backlog items
2. 每個 item 估算 Story Points（1/2/3/5/8）
3. 規劃 Sprint 1（2 週內能完成什麼？）
4. 決定 Definition of Done：什麼叫「完成」？

---

## Lesson 31：GitHub Issues 專案管理

### User Story 格式

```markdown
## 標題：[功能] 實作使用者登入（JWT）

## 使用者故事
**身為** 已註冊的用戶
**我希望** 能用 email + 密碼登入系統
**以便** 我能存取需要認證的功能

## 驗收條件（Acceptance Criteria）
- [ ] POST /auth/login 接受 {email, password}
- [ ] 成功回傳 {token, expires_in}
- [ ] 密碼錯誤回傳 401（不能洩露「帳號存在但密碼錯」的資訊）
- [ ] token 24 小時後過期
- [ ] 密碼用 bcrypt 驗證（不是明文比對）

## 技術備註
- Secret key 從環境變數 JWT_SECRET 讀取
- 需要 users 資料表（email UNIQUE）

## Story Points：5
## Labels：feat, backend, auth, priority-high
## Milestone：Sprint 1
```

### 期末專案 Issues 交付規格

| 交付項目 | 說明 |
|---------|------|
| 10 個 Issues | 每個都有 User Story + AC |
| 2 個 Milestones | Sprint 1（核心功能）/ Sprint 2（進階功能） |
| Labels | 至少使用：feat / fix / docs / priority-high / backend / frontend |

---

# Unit 12：AI 整合與職涯路線 {#unit-12}

## Lesson 32：ML 專案流程（客戶流失預測）

### 標準 ML 流程

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import Pipeline

# ── Step 1：準備資料 ──
np.random.seed(42)
N = 1000

data = pd.DataFrame({
    'tenure_months': np.random.randint(1, 72, N),
    'monthly_charges': np.random.uniform(20, 120, N),
    'num_products': np.random.randint(1, 6, N),
    'has_support': np.random.choice([0, 1], N),
    'contract': np.random.choice(['Monthly','Annual','Biennial'], N),
})
# 模擬流失行為（月付 + 費用高 + 新客 → 更容易流失）
churn_prob = (
    (data['contract'] == 'Monthly').astype(float) * 0.3 +
    (data['monthly_charges'] > 70).astype(float) * 0.2 +
    (data['tenure_months'] < 12).astype(float) * 0.2 +
    np.random.uniform(0, 0.3, N)
)
data['churn'] = (churn_prob > 0.45).astype(int)
print(f"流失率：{data['churn'].mean():.1%}")

# ── Step 2：特徵工程 ──
le = LabelEncoder()
data['contract_enc'] = le.fit_transform(data['contract'])
data['is_new'] = (data['tenure_months'] < 12).astype(int)

# ── Step 3：建立模型（用 Pipeline 避免 data leakage）──
FEATURES = ['tenure_months','monthly_charges','num_products',
            'has_support','contract_enc','is_new']
X, y = data[FEATURES], data['churn']
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
])
pipeline.fit(X_train, y_train)

# ── Step 4：評估 ──
y_pred = pipeline.predict(X_test)
y_prob = pipeline.predict_proba(X_test)[:, 1]

print("\n=== 模型評估 ===")
print(classification_report(y_test, y_pred, target_names=['未流失','流失']))
print(f"AUC-ROC: {roc_auc_score(y_test, y_prob):.4f}")

# ── Step 5：特徵重要性 → 商業洞察 ──
importances = pd.DataFrame({
    'feature': FEATURES,
    'importance': pipeline.named_steps['clf'].feature_importances_
}).sort_values('importance', ascending=False)

print("\n特徵重要性：")
for _, row in importances.iterrows():
    bar = '█' * int(row['importance'] * 60)
    print(f"  {row['feature']:20s} {bar} {row['importance']:.4f}")
```

### 評估指標解讀

```
分類報告說明：

              precision  recall  f1-score
  未流失          P         R      F1      ← 對預測為「未流失」的準確度
  流失            P         R      F1      ← 我們最關心的類別

Precision（精確率）= 預測為流失的人中，真的流失的比例
  → 太低 = 誤判太多（花了行銷成本但那個客戶根本不打算走）

Recall（召回率）= 真正流失的人中，被我們抓到的比例
  → 太低 = 漏掉太多（沒挽留到的客戶默默離開了）

AUC-ROC：0.5 = 瞎猜，1.0 = 完美，通常 > 0.8 算不錯
```

### 課後作業

1. 把 `RandomForestClassifier` 換成 `GradientBoostingClassifier`，比較 AUC 差異
2. 刪掉 `is_new` 這個特徵，看看效果有多大影響？寫出你的結論

---

## Lesson 33：AI API 整合

### 三個整合模式

```python
import anthropic
import json

client = anthropic.Anthropic()  # 使用 ANTHROPIC_API_KEY 環境變數

# ─────────────────────────────────────
# 模式 1：智能客服（結構化 context）
# ─────────────────────────────────────
def ai_support(question: str, order_context: dict) -> str:
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system="""你是電商客服專員，用繁體中文回答。
根據訂單資訊回答，若資訊不足請說明需要什麼。
保持友善、專業、簡潔（不超過 150 字）。""",
        messages=[{
            "role": "user",
            "content": f"客戶問題：{question}\n\n訂單資訊：\n{json.dumps(order_context, ensure_ascii=False, indent=2)}"
        }]
    )
    return msg.content[0].text

# ─────────────────────────────────────
# 模式 2：Code Review 助手（結構化輸出）
# ─────────────────────────────────────
def code_review(code: str, lang: str = "Python") -> dict:
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=f"""你是資深 {lang} 工程師，請審查程式碼。
用繁體中文，以 JSON 格式回應：
{{"issues": [{{"type": "bug|security|performance|style", "line": N, "desc": "...", "fix": "..."}}], "summary": "...", "score": 0-10}}
只回傳 JSON，不要其他文字。""",
        messages=[{"role": "user", "content": f"```{lang.lower()}\n{code}\n```"}]
    )
    raw = msg.content[0].text
    try:
        return json.loads(raw[raw.find('{'):raw.rfind('}')+1])
    except json.JSONDecodeError:
        return {"raw": raw}

# ─────────────────────────────────────
# 模式 3：資料摘要（分析洞察）
# ─────────────────────────────────────
def summarize_data(summary_text: str, question: str) -> str:
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"以下是銷售資料摘要：\n{summary_text}\n\n問題：{question}\n\n請提供洞察與具體建議。"
        }]
    )
    return msg.content[0].text
```

### 重要注意事項（README 必須包含）

```markdown
## AI API 整合注意事項

1. **API Key 安全**
   - ❌ 不要把 key 寫進程式碼或 commit 到 git
   - ✅ 用環境變數：`export ANTHROPIC_API_KEY=sk-...`
   - ✅ 加進 `.gitignore`：`.env` 檔案

2. **成本控制**
   - 每次 API 呼叫都有費用，測試時用 `max_tokens=200`
   - 生產環境要加 @retry 裝飾器處理瞬間失敗

3. **提示詞工程**
   - system prompt 要明確說明角色和輸出格式
   - 結構化輸出要加「只回傳 JSON，不要其他文字」

4. **AI 的限制**
   - AI 可能「幻覺」（說出聽起來合理但錯誤的東西）
   - 關鍵決策不要 100% 依賴 AI 輸出，要有人工確認
```

---

## Lesson 34：職涯路線圖

### 五條路徑地圖

| 路徑 | 核心技能 | 入門薪資（台灣） | 最需要的作品 |
|------|---------|----------------|------------|
| **後端工程師** | Python/Java, DB, API, Docker | NT$45K–65K | 含 API + DB 的完整後端 |
| **資料分析師** | SQL, Python/R, Tableau | NT$40K–55K | 分析報告 + 視覺化 |
| **資料科學家** | ML, 深度學習, 統計 | NT$50K–75K | Kaggle 競賽 + 模型專案 |
| **IT 顧問/PM** | 系統分析, 溝通, 業務 | NT$38K–55K | 系統設計文件 + 流程改善 |
| **資安工程師** | 網路, 滲透測試, 資安框架 | NT$45K–65K | CTF 競賽 + 資安稽核 |

### 四年學習時間軸

```
大一（地基）：
  ☐ 完成 Unit 1-4（計算思維、Python、Git）
  ☐ 建立 GitHub 帳號，養成每週 commit 習慣
  ☐ 探索你有興趣的領域：電商？金融？社會企業？

大二（技術深化）：
  ☐ 完成 Unit 5-8（Git、系統設計、SQL、資料分析）
  ☐ 學會 SQL 進階查詢（Window Functions）
  ☐ 完成一個含 DB 的個人後端專案
  ☐ 目標：找到暑期實習（哪怕是行政，看到「真實」的 IT 環境）

大三（整合應用）：
  ☐ 完成 Unit 9-12（NoSQL、資安、Agile、ML）
  ☐ 參加校內黑客松或系上競賽
  ☐ 期末專案做成真實可用的系統（不是只能在本機跑）
  ☐ 考 1-2 張證照（AWS Cloud Practitioner / Google Data Analytics）

大四（職涯準備）：
  ☐ 畢業專題：解決真實問題，最好有實際使用者
  ☐ 面試準備：LeetCode Easy-Medium + 系統設計 + 行為面試
  ☐ 建立技術部落格或 LinkedIn，定期分享學習成果
  ☐ 參加業界 Meetup，認識在業界工作的學長姊
```

### 交付：個人職涯路線圖（1 頁）

```markdown
# 我的職涯路線圖

## 我選擇的路徑
（後端工程師 / 資料分析師 / 資料科學家 / 顧問PM / 資安工程師）

## 我目前的能力證據
| 技能 | 證據（repo / 課程 / 專案） | 自評（1-5） |
|------|--------------------------|-----------|
| Python | ch04 作業、圖書館系統 | 3 |
| SQL | ch07 電商 DB 作業 | 2 |
| ... | ... | ... |

## 接下來 8 週的補強計畫
| 週次 | 目標 | 具體行動（3 件事） |
|------|------|-----------------|
| Week 1 | 補強 SQL | LeetCode DB 5 題、完成 Window Function 練習、... |
| Week 2 | ... | ... |
| ... | ... | ... |

## 我的期末專案與職涯連結
「我做的 [專案名稱] 展示了我有 [技能A] 和 [技能B]，
這與 [目標職缺] 需要的 [需求] 直接相關。」
```

---

## Lesson 35：期末 Demo Day

### 發表格式（每人 5–7 分鐘）

| 時間 | 內容 |
|------|------|
| 1 分鐘 | 我解決了什麼問題？（不要說「我做了一個電商系統」，說「我解決了 XXX 的 XXX 問題」） |
| 2 分鐘 | 系統架構（架構圖 + DB Schema + API 截圖） |
| 1–2 分鐘 | 我做了哪些分析/洞察（展示圖表和結論） |
| 1 分鐘 | 品質與安全（你如何處理？）|
| 30 秒 | 如果再多一週，你會做什麼？ |

### 期末評分矩陣

| 維度 | 出色（A） | 良好（B） | 及格（C） | 分數 |
|------|---------|---------|---------|------|
| **可運作性** | 所有功能可 demo，零崩潰 | 大部分功能可用 | 至少核心功能運作 | /25 |
| **技術深度** | 有設計取捨說明，知道缺點 | 功能完整，能解釋架構 | 完成基本功能 | /25 |
| **文件品質** | README + ERD + API 文件完整 | README 清楚 | 有 README | /20 |
| **分析洞察** | 洞察有業務意義，有數字支撐 | 有圖表和結論 | 有圖表 | /15 |
| **資安意識** | 有資安檢核清單，主動說明取捨 | 避免明顯漏洞 | 有密碼雜湊 | /15 |

---

# 期末整合專案規格 {#capstone}

## 題目：小型電商系統（含分析與 AI 助理）

### 必備功能（缺一不可）

| 功能 | 規格 |
|------|------|
| **API** | 至少 6 個 endpoints（商品/訂單/客戶各 2 個以上） |
| **DB** | customers / products / orders / order_items（3NF） |
| **交易** | `create_order` 必須用 transaction（rollback 測試） |
| **快取** | 至少 1 個查詢用 cache（mock 或 Redis 皆可） |
| **分析** | 月營收趨勢圖 + RFM 客戶分群結果 |
| **資安** | 參數化查詢 + bcrypt 密碼雜湊 + JWT 登入示範 |
| **文件** | 架構圖 + ERD + API 文件（Markdown 格式） |

### 選配（加分，每項 +5 分）

| 加分項目 | 說明 |
|---------|------|
| 短網址功能 | 整合 Lesson 17 的實作 |
| Rate Limiting | 保護登入 API |
| AI 客服 | 用訂單 context 回答用戶問題 |
| Docker 部署 | `docker-compose up` 可運行 |
| GitHub Actions | 至少一個 CI 測試流程 |

### 資料夾結構

```
capstone-project/
├── README.md               # 專案說明、執行方式、架構說明
├── docs/
│   ├── architecture.md     # 系統架構圖（文字或 mermaid）
│   ├── erd.md              # Entity-Relationship 圖
│   ├── api.md              # API 文件（每個 endpoint 有範例）
│   └── security-checklist.md  # 資安檢核清單（自評）
├── src/
│   ├── database.py         # DB 操作（EcommerceDB 類別）
│   ├── api.py              # Flask API
│   ├── analysis.py         # pandas 分析腳本
│   ├── cache.py            # 快取層
│   └── auth.py             # JWT + bcrypt
├── tests/
│   └── test_create_order.py  # 至少這個要有測試
└── requirements.txt
```

### `security-checklist.md` 模板

```markdown
# 資安自評清單

| 項目 | 狀態 | 說明 |
|------|------|------|
| SQL 使用參數化查詢 | ✅ | 所有 SQL 都用 ? 佔位符 |
| 密碼用 bcrypt 雜湊 | ✅ | rounds=12 |
| JWT 有設定過期時間 | ✅ | exp = 24h |
| Secret key 不在程式碼中 | ✅ | 從 os.environ 讀取 |
| 輸入有驗證 | ✅ | 用 validate_email() |
| HTTPS（若有部署） | ⬜ | 本次作業未部署 |
| Rate Limiting | ⬜ | 未實作（選配） |

## 已知限制
- 本次沒有實作 CSRF 保護
- XSS 防護僅在前端（本次無前端，後端 API 不適用）
```

---

# 作品集結構建議 {#portfolio}

```
im-learning-portfolio/
│
├── README.md                          ← 首頁：學習目標、章節索引、作者資訊
│
├── ch01-computational-thinking/
│   ├── README.md                      ← 學到什麼、遇到的坑、下一步
│   ├── algorithm_chinese.md           ← 練習 1-1
│   ├── score_analyzer.py
│   └── benchmark_duplicates.py        ← 練習 1-2
│
├── ch02-data-structures/
│   ├── README.md
│   ├── decision_table.md
│   └── library_system.py             ← Lesson 4 專案（tag: v0.1-library）
│
├── ch03-os-network/
│   ├── README.md
│   ├── thread_race.py
│   └── api_client.py
│
├── ch04-python/
│   ├── README.md
│   ├── comprehension_exercises.py
│   ├── generator_benchmark.py
│   ├── decorators.py
│   ├── order_model.py
│   └── refactor_students/
│       ├── original.py
│       ├── version1.py               ← 最小改動
│       └── version2.py               ← dataclass 進階版
│
├── ch05-git/                         ← Lesson 14 里程碑
│   └── README.md                     ← Git 工作流筆記
│
├── ch06-system-design/
│   ├── README.md
│   ├── design_questions.md           ← 短網址設計思考
│   └── url_shortener.py
│
├── ch07-database-sql/
│   ├── README.md
│   ├── schema.sql
│   ├── queries.sql                   ← 所有練習的 SQL
│   └── ecommerce_db.py              ← EcommerceDB 類別
│
├── ch08-data-analysis/
│   ├── README.md
│   ├── eda.py
│   ├── rfm_analysis.py
│   ├── sales_dashboard.png
│   └── report.md
│
├── ch09-nosql/
│   ├── README.md
│   └── redis_patterns.py
│
├── ch10-system-analysis-security/
│   ├── README.md
│   ├── uml_diagrams.md
│   ├── flask_api.py
│   ├── sqli_demo.py
│   ├── password_hashing.py
│   ├── jwt_demo.py
│   └── input_validation.py
│
├── ch11-project-management/
│   └── README.md                     ← Scrum 筆記 + Sprint Planning 記錄
│
├── ch12-ai-career/
│   ├── README.md
│   ├── ml_churn.py
│   ├── ai_integration_notes.md
│   └── career_roadmap.md             ← Lesson 34 職涯路線圖
│
└── capstone-project/                 ← 期末整合專案
    ├── README.md
    ├── docs/
    ├── src/
    └── tests/
```

---

## 參考學習資源

**程式設計**
- 書籍：《Python Crash Course》（入門）、《流暢的 Python》（進階）
- 練習：LeetCode（從 Easy 開始）、HackerRank

**資料庫**
- 線上：SQLBolt（互動式 SQL 學習）
- 練習：LeetCode Database 題庫

**資料分析**
- 書籍：《Python for Data Analysis》（pandas 官方作者著）
- 線上：Kaggle Learn（免費，有真實資料集）

**系統設計**
- 書籍：《Designing Data-Intensive Applications》（進階必讀）
- 線上：System Design Primer（GitHub，免費）

**AI / ML**
- 課程：Coursera Machine Learning Specialization（Andrew Ng）
- 線上：fast.ai（實用主義，從程式碼學起）

---

*本手冊版本：2025 年版*
*建議每學期結束後 review 一次，更新作品集連結與學習反思*
