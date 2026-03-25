# Head First Supabase E-Commerce Database

> **"如果你的資料庫設計得好，程式碼就寫得少。"**

歡迎來到這份教學指南。我們要從零開始，用 10 個 Stage 蓋出一個**真正能上線的電商資料庫**。

不是玩具。不是 demo。是你真的可以拿去接金流、管庫存、跑 RLS 的那種。

---

## 這份指南適合誰？

你如果符合以下任一條件，這份指南就是為你寫的：

- 聽過 Supabase 但還沒真正設計過 schema
- 寫過 SQL 但不確定「Supabase 原生」該怎麼做
- 想把舊系統（SQL Server / MySQL / WordPress）搬到 Supabase
- 想理解為什麼電商資料庫要「這樣」設計

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| [`002_shop_schema.sql`](../migrations/002_shop_schema.sql) | 完整可執行的 SQL schema（v3.0, 1,091 行） |
| [`01_foundation-identity.md`](01_foundation-identity.md) | Stage 1-2：地基 + 身分橋接 |
| [`02_organization-catalog.md`](02_organization-catalog.md) | Stage 3-4：組織層級 + 商品建模 |
| [`03_taxonomy-inventory.md`](03_taxonomy-inventory.md) | Stage 5-6：分類系統 + 庫存模式 |
| [`04_coupons-commerce.md`](04_coupons-commerce.md) | Stage 7-8：折扣券 + 交易核心 |
| [`05_security-rls.md`](05_security-rls.md) | Stage 9：RLS 安全完整攻略 |
| [`06_automation.md`](06_automation.md) | Stage 10：Trigger、Realtime、Storage |

**使用方式**：邊讀章節，邊打開 `.sql` 檔案對照。每個 Stage 都標註了對應的 SQL 行號。

> **⚠️ 重要：Schema 命名空間**
>
> 所有表都建在 **`shop`** schema 底下，**不是 `public`**。
>
> ```sql
> -- ✅ 正確：shop.products, shop.orders, shop.users
> SELECT * FROM shop.products;
>
> -- ❌ 錯誤：不要用 public
> SELECT * FROM public.products;  -- 這張表不存在
> ```
>
> 這是刻意的設計——把業務邏輯和 Supabase 內建的 `public` schema 隔開。
> 唯一在 `public` 的是 `generate_ulid()` 函式（因為它是跨 schema 共用的）。

---

## 全景地圖

先看大局。這 20 張表分成 10 個 Stage，每個 Stage 學一個核心概念：

```
Stage 1   Foundation        ── 地基（ULID、enum、extensions）        SQL 34-71
Stage 2   Identity          ── 誰是誰（auth bridge）                SQL 74-192
Stage 3   Organization      ── 公司 → 門市 → 店員                   SQL 195-263
Stage 4   Catalog           ── 商品目錄                              SQL 266-353
Stage 5   Taxonomy          ── 分類系統                              SQL 356-402
Stage 6   Inventory         ── 庫存快照 + 異動紀錄                   SQL 405-445
Stage 7   Coupons & Addr    ── 折扣券 & 地址簿                       SQL 448-504
Stage 8   Commerce          ── 訂單、付款、紅利點數                   SQL 507-643
Stage 9   Security          ── RLS、Policy、GRANT                   SQL 646-1012
Stage 10  Automation        ── Trigger、Realtime、Storage           SQL 1015-1091
```

它們的依賴關係長這樣：

```
                    ┌─────────────┐
                    │  auth.users │  (Supabase 管理)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ shop.users  │  Stage 2 (ULID bridge)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │shop.profiles│  Stage 2
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  companies  │ │  products   │ │  addresses  │
    │  Stage 3    │ │  Stage 4    │ │  Stage 7    │
    └──────┬──────┘ └──┬─────┬───┘ └──────┬──────┘
           │           │     │            │
    ┌──────▼──────┐    │  ┌──▼─────┐ ┌────▼──────┐
    │   stores    │    │  │reviews │ │  orders   │
    │  Stage 3    │    │  │Stage 4 │ │  Stage 8  │
    └──────┬──────┘    │  └────────┘ └──┬──┬──┬──┘
           │           │                │  │  │
    ┌──────▼──────┐ ┌──▼───────┐    ┌──▼┐ │ ┌▼────────┐
    │ store_staff │ │  stocks  │    │OI │ │ │payments │
    │  Stage 3    │ │ Stage 6  │    │S8 │ │ │ Stage 8 │
    └─────────────┘ └──────────┘    └───┘ │ └─────────┘
                                          │
                                   ┌──────▼──────┐
                                   │point_rewards│
                                   │  Stage 8    │
                                   └─────────────┘
```

---

## 設計原則速查表

| # | 原則 | 做法 |
|---|------|------|
| 1 | PK 一致性 | `TEXT DEFAULT public.generate_ulid()` — 所有業務表 |
| 2 | Auth 解耦 | `shop.users` bridge 表，業務表不碰 `auth.users` |
| 3 | Schema 隔離 | 所有業務表在 `shop` schema，不在 `public` |
| 4 | 型別一致 | FK 全部 `TEXT`，不混用 UUID/BIGINT |
| 5 | 查詢欄位獨立 | 會被 WHERE/ORDER BY 的欄位不放 jsonb |
| 6 | DB 層驗證 | Named CHECK + Enum types |
| 7 | RLS helper | Policy 不寫 JOIN，抽成 SECURITY DEFINER function |
| 8 | `(SELECT auth.uid())` | RLS 裡永遠加括號，initPlan 最佳化 |
| 9 | 完整安全三層 | RLS enable + Policy + GRANT，缺一不可 |
| 10 | service_role policy | 每張表都要，ETL/cron 才能用 |
| 11 | Soft delete | 核心表用 `deleted_at`，append-only 表永不刪除 |
| 12 | 快照 + 日誌 | stocks（當前）+ movements（歷史） |
| 13 | Ledger 模式 | 只存交易，餘額用 SUM 算 |
| 14 | FK 建表順序 | 被引用的表先建 |
| 15 | GRANT EXECUTE | helper function 必須授權 |
| 16 | `search_path` 鎖定 | 所有 SECURITY DEFINER function 都設 `SET search_path = shop` |

---

## 進階挑戰（想更深入的人）

完成這份 schema 後，你可以嘗試：

1. **Partition**：如果 `inventory_movements` 或 `point_rewards` 預期年增 >1M 列，考慮 `PARTITION BY RANGE (created_at)`
2. **Read Replica**：分析查詢（報表、Dashboard）打 read replica，不要打主庫
3. **Edge Functions**：用 Supabase Edge Functions 處理付款回調（webhook → 更新 payment status）
4. **Database Functions**：把「建立訂單 + 扣庫存 + 記錄 movement」包成一個 `plpgsql` function，確保原子性
5. **Full-Text Search**：用 `to_tsvector` + `ts_rank` 做商品搜尋排序

---

## 參考資源

- **Schema SQL**：[`002_shop_schema.sql`](../migrations/002_shop_schema.sql)
- **Supabase 設計規範**：`../../agent-init/skills/supabase/` 目錄
  - `pk-convention.md` — ULID 主鍵慣例
  - `rls-patterns.md` — RLS 正確寫法
  - `anti-patterns.md` — 反模式清單
  - `migration-guidelines.md` — Migration 規範
  - `performance-linter.md` — 效能守門員
  - `query-patterns.md` — 查詢模式
  - `scaling-guidelines.md` — 擴展紅線
