---
name: supabase-rls-basics
description: "RLS 入門：auth.uid() 基礎模式、Policy 寫法、最少安全要求"
triggers:
  - "RLS"
  - "row level security"
  - "policy"
  - "權限"
  - "安全"
finish_conditions:
  - "表已啟用 RLS"
  - "至少有 SELECT 和 INSERT policy"
  - "Policy 使用 auth.uid() 做使用者隔離"
references:
  - docs/supabase/labs/lab-04-rls.md
  - docs/supabase/assignments/hw-04-rls-advanced.md
  - docs/supabase/chapter-04-project-practice.md
---

# RLS Basics（基礎）

> 最低限度的安全：讓每個使用者只看到自己的資料。

---

## 快速開始

三步驟啟用 RLS：

```sql
-- 1. 啟用 RLS
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

-- 2. 建立 Policy：使用者只能讀自己的資料
CREATE POLICY "Users can read own predictions"
  ON predictions FOR SELECT
  USING (auth.uid() = user_id);

-- 3. 建立 Policy：使用者只能新增自己的資料
CREATE POLICY "Users can insert own predictions"
  ON predictions FOR INSERT
  WITH CHECK (auth.uid() = user_id);
```

---

## 目的 / 能解決什麼問題

防止使用者 A 看到使用者 B 的資料。在 Supabase 中，**沒有 RLS = 所有 authenticated 使用者可看到所有資料**。

## 何時該用 / 何時不該用

| 該用 | 不該用 |
|------|--------|
| 任何有 user_id 的表 | 公開資料表（如：產品目錄）|
| 作業 hw-04 | 純本地開發測試（但仍建議啟用）|
| 期末專題 | — |

## Repo Reality

- `docs/supabase/labs/lab-04-rls.md` — RLS 實驗：videos 表 + auth.uid()
- `docs/supabase/assignments/hw-04-rls-advanced.md` — 進階 RLS：4 種 Policy（SELECT/INSERT/UPDATE/DELETE）
- `docs/supabase/chapter-04-project-practice.md` — predictions 表的 RLS

---

## 核心規則

### 1. 一定要啟用 RLS

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
```

**沒有例外**。忘記這一步 = 全部使用者可以讀寫全部資料。

### 2. Policy 結構

```sql
CREATE POLICY "<描述性名稱>"
  ON <table>
  FOR <operation>           -- SELECT / INSERT / UPDATE / DELETE / ALL
  TO <role>                 -- authenticated / anon / 省略則對所有 role
  USING (<讀取條件>)        -- SELECT, UPDATE, DELETE 用
  WITH CHECK (<寫入條件>);  -- INSERT, UPDATE 用
```

### 3. 基礎四 Policy 模式（hw-04 教的）

```sql
-- 讀取：只能讀自己的
CREATE POLICY "select_own" ON predictions
  FOR SELECT TO authenticated
  USING (auth.uid() = user_id);

-- 新增：只能新增自己的
CREATE POLICY "insert_own" ON predictions
  FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- 更新：只能改自己的
CREATE POLICY "update_own" ON predictions
  FOR UPDATE TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 刪除：只能刪自己的
CREATE POLICY "delete_own" ON predictions
  FOR DELETE TO authenticated
  USING (auth.uid() = user_id);
```

### 4. `auth.uid()` 是什麼？

`auth.uid()` 回傳當前登入使用者的 UUID。Supabase 自動從 JWT token 中提取。

```
使用者 A 登入 → JWT 含 user_id = 'abc-123'
              → auth.uid() 回傳 'abc-123'
              → Policy 只允許 user_id = 'abc-123' 的列
```

### 5. 公開讀取 + 私有寫入

如果某些資料需要公開讀取（如產品目錄）：

```sql
-- 任何人可讀
CREATE POLICY "public_read" ON products
  FOR SELECT
  USING (true);

-- 只有 authenticated 可寫
CREATE POLICY "auth_insert" ON products
  FOR INSERT TO authenticated
  WITH CHECK (true);
```

---

## 常見錯誤與排除

| 錯誤 | 症狀 | 解決方式 |
|------|------|---------|
| 忘記啟用 RLS | 所有使用者看到所有資料 | `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` |
| 只有 SELECT policy | INSERT/UPDATE/DELETE 被擋 | 補上其他 operation 的 policy |
| `USING` vs `WITH CHECK` 搞混 | INSERT 失敗或 SELECT 漏資料 | 讀用 USING，寫用 WITH CHECK |
| user_id 型別不匹配 | Policy 永遠 false | 確保 user_id 與 auth.uid() 型別一致（都是 UUID）|

---

## 從基礎到進階

| 你在這裡 | 下一步 |
|---------|--------|
| `auth.uid() = user_id` | 學 `(SELECT auth.uid())` 效能優化 |
| 直接 USING 判斷 | 學 helper function 模式 |
| 單一使用者隔離 | 學多租戶 project_id scoping |
| 無 GRANT | 學 GRANT SELECT/INSERT/UPDATE/DELETE |

進階內容見 `production/rls-patterns.md`。

## 參考來源

- `docs/supabase/labs/lab-04-rls.md` — RLS 實驗
- `docs/supabase/assignments/hw-04-rls-advanced.md` — 四 Policy 完整範例
- Supabase 官方文件 — Row Level Security
