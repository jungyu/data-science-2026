# Ch02：核心概念 — Series 與 DataFrame

> **本章目標**：搞懂 Pandas 的兩個核心資料結構，學會建立、存取、操作它們。

---

## 🧱 Pandas 的兩塊積木

想像你在用 Excel：

- **一個欄位**（例如「成績」那一欄） → 這就是 **Series**
- **整張工作表**（有多個欄位的表格） → 這就是 **DataFrame**

```
Series（一維）          DataFrame（二維）
┌───────┐              ┌───────┬──────┬──────┐
│  85   │              │ 姓名  │ 成績 │ 班級 │
│  92   │              ├───────┼──────┼──────┤
│  78   │              │ 小明  │  85  │  A   │
│  88   │              │ 小華  │  92  │  B   │
│  95   │              │ 小美  │  78  │  A   │
└───────┘              │ 小強  │  88  │  B   │
                       │ 小芳  │  95  │  A   │
                       └───────┴──────┴──────┘
```

---

## 📦 Series：一維資料容器

### 建立 Series

```python
import pandas as pd

# 方法 1：從 list 建立
scores = pd.Series([85, 92, 78, 88, 95])
print(scores)
```

輸出：
```
0    85
1    92
2    78
3    88
4    95
dtype: int64
```

注意看左邊的 `0, 1, 2, 3, 4` — 那就是**索引 (index)**。

### 自訂索引

```python
# 方法 2：指定索引
scores = pd.Series(
    [85, 92, 78, 88, 95],
    index=["小明", "小華", "小美", "小強", "小芳"]
)
print(scores)
```

輸出：
```
小明    85
小華    92
小美    78
小強    88
小芳    95
dtype: int64
```

### 從字典建立

```python
# 方法 3：從 dict 建立（key 自動變成 index）
scores = pd.Series({
    "小明": 85,
    "小華": 92,
    "小美": 78
})
```

### 存取 Series 的值

```python
# 用索引名稱
scores["小明"]       # → 85

# 用位置
scores.iloc[0]       # → 85

# 切片
scores["小明":"小美"] # → 小明 85, 小華 92, 小美 78（包含結尾！）
scores.iloc[0:2]     # → 小明 85, 小華 92（不包含結尾）
```

> ⚠️ **注意**：用名稱切片會**包含結尾**，用位置切片**不包含結尾**。
> 這是初學者最常搞混的地方！

### Series 的常用屬性

```python
scores.values    # 底層 NumPy 陣列：array([85, 92, 78, 88, 95])
scores.index     # 索引：Index(['小明', '小華', '小美', '小強', '小芳'])
scores.dtype     # 資料型態：int64
scores.shape     # 形狀：(5,)
scores.name      # 名稱（可設定）
```

### Series 向量化運算

```python
# 不需要寫迴圈！
scores + 5          # 全部加 5
scores * 1.1        # 全部乘 1.1
scores > 80         # 回傳布林 Series
scores[scores > 80] # 篩選出 > 80 的值
```

---

## 📊 DataFrame：二維表格資料

### 建立 DataFrame

```python
# 方法 1：從字典建立（最常用）
data = {
    "姓名": ["小明", "小華", "小美", "小強", "小芳"],
    "成績": [85, 92, 78, 88, 95],
    "班級": ["A", "B", "A", "B", "A"]
}
df = pd.DataFrame(data)
print(df)
```

輸出：
```
   姓名  成績 班級
0  小明   85   A
1  小華   92   B
2  小美   78   A
3  小強   88   B
4  小芳   95   A
```

### 其他建立方式

```python
# 方法 2：從 list of dicts
data = [
    {"姓名": "小明", "成績": 85, "班級": "A"},
    {"姓名": "小華", "成績": 92, "班級": "B"},
]
df = pd.DataFrame(data)

# 方法 3：從 NumPy array
import numpy as np
df = pd.DataFrame(
    np.random.randint(60, 100, size=(5, 3)),
    columns=["國文", "英文", "數學"]
)

# 方法 4：從 CSV 檔案（最實際的方式！）
df = pd.read_csv("data/orders.csv")
```

---

## 🔍 DataFrame 的結構解剖

```
             columns（欄位名稱）
            ┌──────┬──────┬──────┐
            │ 姓名 │ 成績 │ 班級 │
index ──→ 0 │ 小明 │  85  │  A   │ ← 一列 = 一筆資料
(索引)    1 │ 小華 │  92  │  B   │
          2 │ 小美 │  78  │  A   │
            └──────┴──────┴──────┘
                │
                ↓
            每一欄就是一個 Series
```

### 基本屬性

```python
df.shape      # (3, 3) → 3 列 3 欄
df.columns    # Index(['姓名', '成績', '班級'])
df.index      # RangeIndex(start=0, stop=3, step=1)
df.dtypes     # 每個欄位的型態
df.size       # 元素總數：9
df.ndim       # 維度：2
```

---

## 📌 存取資料：三種方式

### 方式一：取出欄位（Column）

```python
# 單一欄位 → 回傳 Series
df["成績"]
df.成績          # 也可以用屬性方式（但欄名有空格或特殊字元時不能用）

# 多個欄位 → 回傳 DataFrame
df[["姓名", "成績"]]
```

### 方式二：`loc` — 用標籤存取

```python
# loc[列標籤, 欄標籤]
df.loc[0, "姓名"]            # → "小明"
df.loc[0:2, "姓名":"成績"]    # 列 0~2，欄 姓名~成績（都包含）
df.loc[df["成績"] > 80]       # 條件篩選
```

### 方式三：`iloc` — 用位置存取

```python
# iloc[列位置, 欄位置]
df.iloc[0, 0]        # → "小明"（第 0 列第 0 欄）
df.iloc[0:2, 0:2]    # 列 0~1，欄 0~1（不包含結尾）
df.iloc[-1]           # 最後一列
```

### 🎯 `loc` vs `iloc` 比較

| 特性 | `loc` | `iloc` |
|------|-------|--------|
| 存取方式 | 標籤（名稱） | 位置（數字） |
| 切片包含結尾？ | ✅ 包含 | ❌ 不包含 |
| 支援布林索引？ | ✅ | ✅ |
| 使用情境 | 知道欄位名稱時 | 知道位置時 |

> 💡 **記憶技巧**：**loc** = **l**abel-based, **iloc** = **i**nteger-based

---

## ✏️ 修改與新增

### 新增欄位

```python
# 直接賦值
df["是否及格"] = df["成績"] >= 60

# 用 assign（不修改原 DataFrame）
df2 = df.assign(加權成績=df["成績"] * 1.1)
```

### 修改值

```python
# 修改單一值
df.loc[0, "成績"] = 90

# 條件修改
df.loc[df["成績"] < 60, "成績"] = 60  # 不及格的都改成 60
```

### 刪除

```python
# 刪除欄位
df = df.drop(columns=["是否及格"])

# 刪除列
df = df.drop(index=[0, 1])
```

---

## 🧪 動手練習

### 練習 1：建立你的第一個 DataFrame

```python
# 建立一個包含 5 位同學的成績表
# 欄位：姓名、國文、英文、數學
# 你來填資料！

data = {
    "姓名": [____],
    "國文": [____],
    "英文": [____],
    "數學": [____],
}
df = pd.DataFrame(data)
```

### 練習 2：存取練習

```python
# 1. 取出「英文」欄位
# 2. 取出第 2 位同學的所有成績
# 3. 取出國文成績 > 80 的同學
# 4. 新增一欄「平均」= (國文 + 英文 + 數學) / 3
```

### 練習 3：用教學資料集

```python
# 讀取訂單資料
orders = pd.read_csv("data/orders.csv")

# 1. 這張表有幾列幾欄？
# 2. 取出前 5 筆訂單的 order_id 和 unit_price
# 3. 找出 quantity > 3 的訂單
# 4. 新增欄位 total_price = quantity * unit_price * (1 - discount)
```

---

## ❗ 常見錯誤與陷阱

### 陷阱 1：`SettingWithCopyWarning`

```python
# ❌ 這樣寫會出警告
subset = df[df["成績"] > 80]
subset["等級"] = "優"

# ✅ 正確做法：用 .copy()
subset = df[df["成績"] > 80].copy()
subset["等級"] = "優"
```

### 陷阱 2：`[]` 取多欄忘記用雙括號

```python
# ❌ 錯誤
df["姓名", "成績"]    # 會出 KeyError

# ✅ 正確
df[["姓名", "成績"]]  # 傳入 list
```

### 陷阱 3：混淆 `loc` 和 `iloc` 的切片行為

```python
# loc 包含結尾
df.loc[0:2]   # 回傳索引 0, 1, 2（三列）

# iloc 不包含結尾
df.iloc[0:2]  # 回傳位置 0, 1（兩列）
```

---

## 🔑 本章重點回顧

| 概念 | 說明 |
|------|------|
| Series | 一維資料容器，像 Excel 的單一欄位 |
| DataFrame | 二維表格，像 Excel 的工作表 |
| index | 列的標籤（預設為 0, 1, 2...） |
| columns | 欄的名稱 |
| `loc` | 用標籤存取，切片包含結尾 |
| `iloc` | 用位置存取，切片不包含結尾 |
| `df["欄"]` | 取出單一欄位（回傳 Series） |
| `df[["欄1", "欄2"]]` | 取出多個欄位（回傳 DataFrame） |

---

## ⏭️ 下一章預告

> **Ch03：資料的進與出**
>
> DataFrame 很好，但你的資料不會憑空出現。
> 下一章學怎麼把 CSV、Excel、JSON 讀進 Pandas，也學怎麼存出來。

---

[← Ch01：為什麼要學 Pandas](ch01-why-pandas.md) | [Ch03：資料的進與出 →](ch03-data-io.md)
