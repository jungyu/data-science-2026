# 附錄 B：Pandas 速查表

> 隨時查閱的快速參考，按使用頻率排列。

---

## 讀取與儲存

```python
# 讀取
df = pd.read_csv("file.csv")
df = pd.read_csv("file.csv", encoding="utf-8", parse_dates=["date"])
df = pd.read_excel("file.xlsx", sheet_name="Sheet1")
df = pd.read_json("file.json")
df = pd.read_sql("SELECT * FROM table", conn)
df = pd.read_parquet("file.parquet")

# 儲存
df.to_csv("out.csv", index=False)
df.to_csv("out.csv", index=False, encoding="utf-8-sig")  # Excel 友善
df.to_excel("out.xlsx", index=False)
df.to_json("out.json", orient="records", force_ascii=False)
df.to_parquet("out.parquet")
```

---

## 觀察資料

```python
df.head(5)              # 前 5 筆
df.tail(5)              # 後 5 筆
df.sample(5)            # 隨機 5 筆
df.shape                # (列數, 欄數)
df.info()               # 完整資訊（型態 + 空值）
df.describe()           # 數值統計
df.describe(include="all")  # 所有欄位統計
df.dtypes               # 各欄位型態
df.columns              # 欄位名稱
df.index                # 索引
df.nunique()            # 各欄位不重複值數量
df["col"].value_counts()    # 值的出現次數
df["col"].unique()          # 所有不重複值
```

---

## 篩選資料

```python
# 條件篩選
df[df["col"] > 5]
df[(df["A"] > 5) & (df["B"] == "x")]       # AND
df[(df["A"] > 5) | (df["B"] == "x")]       # OR
df[~(df["A"] > 5)]                          # NOT

# 進階篩選
df[df["col"].isin(["a", "b", "c"])]         # 值在清單中
df[df["col"].between(1, 10)]                 # 範圍
df[df["col"].str.contains("keyword")]        # 字串包含
df.query("col > 5 and col2 == 'x'")         # SQL 風格

# 存取
df["col"]                # 取出欄位（Series）
df[["col1", "col2"]]     # 取多欄（DataFrame）
df.loc[0, "col"]         # 標籤存取
df.iloc[0, 0]            # 位置存取
df.loc[df["A"] > 5, "B"] # 條件 + 欄位
```

---

## 排序

```python
df.sort_values("col")                        # 升序
df.sort_values("col", ascending=False)       # 降序
df.sort_values(["A", "B"], ascending=[True, False])  # 多欄
df.nlargest(10, "col")                       # Top 10
df.nsmallest(5, "col")                       # Bottom 5
```

---

## 缺失值

```python
df.isnull().sum()                    # 各欄空值數
df.dropna()                          # 刪除有空值的列
df.dropna(subset=["col1", "col2"])   # 指定欄位
df.fillna(0)                         # 填 0
df["col"].fillna(df["col"].median()) # 填中位數
df["col"].ffill()                    # 前值填補
df["col"].bfill()                    # 後值填補
```

---

## 重複值

```python
df.duplicated().sum()                # 重複列數
df.drop_duplicates()                 # 移除重複
df.drop_duplicates(subset=["col"])   # 以特定欄位判斷
```

---

## 型態轉換

```python
df["col"].astype(int)                        # 轉整數
df["col"].astype(float)                      # 轉浮點
df["col"].astype(str)                        # 轉字串
df["col"].astype("category")                 # 轉類別
pd.to_numeric(df["col"], errors="coerce")    # 安全轉數值
pd.to_datetime(df["col"])                    # 轉日期
pd.to_datetime(df["col"], format="%Y-%m-%d") # 指定格式
```

---

## 欄位操作

```python
# 新增
df["new"] = df["A"] * df["B"]
df["new"] = np.where(df["A"] > 5, "高", "低")
df["new"] = pd.cut(df["A"], bins=[0,5,10], labels=["低","高"])

# 修改
df.rename(columns={"old": "new"})
df.loc[df["A"] > 5, "B"] = 999

# 刪除
df.drop(columns=["col"])
df.drop(index=[0, 1])
```

---

## 分組聚合

```python
df.groupby("col")["val"].mean()              # 單一聚合
df.groupby("col")["val"].agg(["sum","mean","count"])  # 多重聚合
df.groupby("col").agg(                       # 具名聚合
    total=("val", "sum"),
    avg=("val", "mean"),
    n=("id", "count")
)
df.groupby("col", as_index=False)["val"].sum()   # 不設索引
df.groupby("col")["val"].transform("mean")       # 保持原形
df.groupby("col").filter(lambda x: len(x) > 5)   # 篩選整組
```

---

## 樞紐分析

```python
pd.pivot_table(df, values="val", index="row", columns="col", aggfunc="sum")
pd.pivot_table(df, values="val", index="row", columns="col",
               aggfunc="sum", fill_value=0, margins=True)
pd.crosstab(df["A"], df["B"])
pd.crosstab(df["A"], df["B"], normalize="index")
```

---

## 合併

```python
df1.merge(df2, on="key")                     # inner join
df1.merge(df2, on="key", how="left")         # left join
df1.merge(df2, left_on="a", right_on="b")    # 不同欄名
pd.concat([df1, df2])                        # 垂直堆疊
pd.concat([df1, df2], axis=1)                # 水平合併
```

---

## 時間序列

```python
# 日期組件
df["date"].dt.year / .month / .day / .dayofweek / .quarter
df["date"].dt.day_name()

# 重採樣（需要 DatetimeIndex）
df.set_index("date")["val"].resample("ME").sum()    # 月
df.set_index("date")["val"].resample("W").mean()    # 週

# 移動平均
df["val"].rolling(7).mean()
df["val"].ewm(span=7).mean()

# 成長率
df["val"].pct_change()

# 時間差
df["date"] + pd.Timedelta(days=7)
(df["date2"] - df["date1"]).dt.days
```

---

## 字串操作

```python
df["col"].str.upper()            # 大寫
df["col"].str.lower()            # 小寫
df["col"].str.strip()            # 去空白
df["col"].str.contains("key")    # 包含
df["col"].str.startswith("A")    # 開頭
df["col"].str.replace("a", "b")  # 替換
df["col"].str.len()              # 長度
df["col"].str.split(",")         # 分割
df["col"].str.extract(r"(\d+)")  # 正則提取
```

---

## 效能技巧

```python
# 向量化 > apply > iterrows
df["new"] = df["A"] * df["B"]                    # 最快
df["new"] = np.where(df["A"] > 0, "Y", "N")     # 快
df["new"] = np.select([c1, c2], ["A", "B"], "C") # 快
df["new"] = df["A"].apply(func)                   # 慢
for i, row in df.iterrows(): ...                  # 最慢

# 記憶體
df["col"] = df["col"].astype("category")     # 重複值多的欄位
df = pd.read_csv("f.csv", usecols=["a","b"]) # 只讀需要的欄
df = pd.read_csv("f.csv", dtype={"a":"int16"})  # 指定小型態

# 大檔案
for chunk in pd.read_csv("big.csv", chunksize=50000):
    process(chunk)
```

---

## 常用 import

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
```

---

[← 附錄 A：教學指南](appendix-teaching-guide.md) | [回目錄 →](README.md)
