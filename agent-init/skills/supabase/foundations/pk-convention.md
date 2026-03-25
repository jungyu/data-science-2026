---
name: supabase-pk-convention-foundations
description: "主鍵慣例入門：從 UUID 開始，理解為什麼進階專案會演進到 ULID"
triggers:
  - "primary key"
  - "id"
  - "uuid"
  - "ulid"
  - "generate_ulid"
finish_conditions:
  - "學生能解釋 UUID 與 ULID 的差異"
  - "學生能在 CREATE TABLE 中正確使用 PK"
references:
  - docs/supabase/chapter-03-supabase-hands-on.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# PK Convention（基礎）

> 先學 UUID，再懂為什麼要 ULID。

---

## 快速開始

課程 ch03-ch04 使用的標準寫法：

```sql
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  input_data JSONB,
  output_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

這是 Supabase 內建支援的寫法，**初學階段完全正確**。

---

## 目的 / 能解決什麼問題

讓學生理解 PK 設計的基本原則，並為進階專案（e-Commerce、Crawler）的 ULID 遷移做準備。

## 何時該用 / 何時不該用

| 該用 | 不該用 |
|------|--------|
| ch01-05 課程作業 | e-Commerce / Crawler 進階教材（改用 production/ 規範）|
| lab01-05 實驗 | 已明確要求使用 ULID 的專案 |
| hw01-04 作業 | 期末專題（建議直接用 ULID）|

---

## Repo Reality

- `docs/supabase/chapter-03-supabase-hands-on.md` — 使用 `UUID DEFAULT gen_random_uuid()`
- `docs/supabase/chapter-04-project-practice.md` — predictions 表使用 UUID
- `docs/supabase/labs/lab-02-postgresql-core.md` — videos 表使用 UUID
- `docs/supabase/e-Commerce/README.md` — Stage 1 開始改用 ULID（進階）
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 1 教從 BIGSERIAL → ULID 的演進

---

## 兩種 PK 策略

### Level 1：UUID（課程基礎）

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

- Supabase 內建支援，不需額外函式
- 與 `auth.users` 型別一致（都是 UUID）
- 隨機不可排序

**適用**：作業、小型專案、快速原型。

### Level 2：ULID（進階 / 期末專題）

```sql
id TEXT PRIMARY KEY DEFAULT generate_ulid()
```

- 需要先定義 `generate_ulid()` 函式（見 Crawler Stage 1）
- 按時間排序 → B-Tree index 效能更好
- 26 字元 Crockford Base32

**適用**：e-Commerce、Crawler 教材、期末專題、任何需要高寫入效能的場景。

### 比較

| 特性 | UUID v4 | ULID |
|------|---------|------|
| 可排序 | ❌ 隨機 | ✅ 按時間 |
| Index 效能 | 一般（隨機寫入，頁分裂） | 佳（順序寫入） |
| 長度 | 36 字元（含 `-`） | 26 字元 |
| 需要額外函式 | ❌ 內建 | ✅ 需定義 `generate_ulid()` |
| 與 auth.users 相容 | ✅ 直接 | 需要 bridge 表 |

---

## 演進路徑

```
ch03 作業    → UUID（直接用 gen_random_uuid()）
  ↓
hw01-04     → UUID（與課程一致）
  ↓
Crawler Stage 1 → 學會 ULID，理解為什麼 BIGSERIAL 不好
  ↓
e-Commerce Stage 1 → ULID 全面啟用 + Auth Bridge 模式
  ↓
期末專題    → 建議 ULID（加分項，非強制）
```

---

## FK 型別一致性（不分 UUID 或 ULID 都適用）

**核心規則**：FK 型別必須與被引用表的 PK 型別一致。

```sql
-- 如果 users.id 是 UUID：
user_id UUID REFERENCES users(id)

-- 如果 users.id 是 TEXT (ULID)：
user_id TEXT REFERENCES users(id)

-- ❌ 混用 → JOIN 會報錯
user_id UUID REFERENCES users(id)  -- 但 users.id 是 TEXT → 型別不匹配
```

---

## 常見錯誤與排除

| 錯誤 | 原因 | 解決方式 |
|------|------|---------|
| `generate_ulid()` does not exist | 未定義函式 | 參考 Crawler Stage 1 的 SQL 定義 |
| FK 型別不匹配 | UUID 引用 TEXT 或反過來 | 確保 PK 和 FK 型別一致 |
| BIGSERIAL 配 UUID FK | 混用自增與 UUID | 統一為 UUID 或 ULID |

## 參考來源

- `docs/supabase/chapter-03-supabase-hands-on.md` — UUID 基礎用法
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 1：ULID 完整教學
- ULID Spec: https://github.com/ulid/spec
