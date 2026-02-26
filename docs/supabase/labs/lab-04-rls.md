# 實驗 4：RLS — 資料科學最重要的一課

---

## 實驗目標

- 理解資料權限控制
- 啟用 Row Level Security
- 建立 Policy

---

## 4.1 什麼是 RLS？

RLS（Row Level Security）= 資料列層級的安全控制。

傳統方式：

```
使用者 → 後端 API → 權限判斷 → 資料庫查詢
```

RLS 方式：

```
使用者 → Supabase API → PostgreSQL 自動過濾（RLS）
```

好處：

- 安全邏輯在資料庫層
- 不用自己寫後端權限
- 無法繞過

---

## 4.2 啟用 RLS

```sql
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
```

啟用後：

- 沒有任何 Policy 的話，所有查詢都會被拒絕
- 必須建立 Policy 才能存取資料

---

## 4.3 建立讀取 Policy

```sql
CREATE POLICY "Public can read"
ON videos
FOR SELECT
USING (true);
```

說明：

- `FOR SELECT` — 只影響讀取操作
- `USING (true)` — 所有人都能讀取

---

## 4.4 建立寫入 Policy

```sql
CREATE POLICY "Authenticated users can insert"
ON videos
FOR INSERT
WITH CHECK (auth.role() = 'authenticated');
```

說明：

- `FOR INSERT` — 只影響寫入操作
- `WITH CHECK` — 必須是已登入使用者

---

## 4.5 進階：使用者只能看到自己的資料

先為 `videos` 加上 `user_id` 欄位：

```sql
ALTER TABLE videos ADD COLUMN user_id UUID;
```

建立 Policy：

```sql
CREATE POLICY "Users can read own videos"
ON videos
FOR SELECT
USING (auth.uid() = user_id);
```

---

## 4.6 測試 RLS

### 測試方式 1：Dashboard

在 Supabase Dashboard 的 Table Editor 中，切換不同角色查看資料變化。

### 測試方式 2：Python

```python
# 使用 anon key（未登入）嘗試查詢
response = supabase.table("videos").select("*").execute()
print(f"查詢到 {len(response.data)} 筆資料")
```

---

## 4.7 RLS 的資料科學意義

| 場景 | 沒有 RLS | 有 RLS |
|------|----------|--------|
| A 客戶查預測結果 | 看到所有人的 | 只看到自己的 |
| 模型輸出 API | 需要後端過濾 | 資料庫自動過濾 |
| 多租戶系統 | 複雜的權限邏輯 | 一條 Policy 搞定 |

---

## 實驗檢核

完成以下項目打勾：

- [ ] 能說明 RLS 的用途
- [ ] 已啟用 RLS
- [ ] 已建立 SELECT Policy
- [ ] 已建立 INSERT Policy
- [ ] 理解 `auth.uid()` 的作用
