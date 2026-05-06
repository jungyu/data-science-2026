# Ch 01：什麼是向量搜尋

> 不需要看懂數學。只需要理解「為什麼 SQL LIKE 不夠用」。

---

## 1-1  你的 bot 收到一個問題

```
使用者：「Next.js 14 在 Vercel 上 hydration 報錯怎麼處理？」
```

**用 SQL LIKE 找答案**：

```sql
SELECT content FROM private_knowledge
WHERE content LIKE '%hydration%'
  AND content LIKE '%Vercel%';
```

結果：可能找不到任何 row——因為知識庫裡的文件可能寫的是：

```
「App Router 的 Client/Server Component 邊界會觸發 mismatch 警告…」
```

這句話沒有 "hydration" 這個詞，但**語意完全相關**。LIKE 看不懂語意，只看字面。

---

## 1-2  向量搜尋的直覺

把每一段文字「壓縮」成一個 1536 維的數字陣列（向量）：

```
"App Router 的 Client/Server Component 邊界會觸發 mismatch 警告"
   → [0.021, -0.045, 0.103, ..., 0.089]   ← 1536 個數字

"Next.js 14 hydration 報錯"
   → [0.019, -0.041, 0.098, ..., 0.091]   ← 1536 個數字
```

這兩個向量的**方向非常接近**（cosine similarity ≈ 0.92）——
即使文字完全不同，向量距離反映的是**語意距離**。

```
╔════════════════════════════════════════╗
║  SQL LIKE  → 找字面符合                ║
║  向量搜尋  → 找語意接近                ║
╚════════════════════════════════════════╝
```

---

## 1-3  這個專案用什麼向量模型？

看 `.env.example`：

```bash
EMBEDDING_MODEL=text-embedding-3-small   # 預設
# EMBEDDING_MODEL=text-embedding-3-large  # 更貴但更準
```

| 模型 | 維度 | 每 1M token 費用 | 適合 |
|------|------|-----------------|------|
| `text-embedding-3-small` | 1536 | $0.020 | 大多數情境 |
| `text-embedding-3-large` | 3072 | $0.130 | 高精度需求 |

本課程全程用 `text-embedding-3-small`（維度 1536，對應 `schema.sql` 的 `vector(1536)`）。

---

## 1-4  向量搜尋 + 關鍵字搜尋 = 混合搜尋

光靠向量有時不夠。例如：

```
使用者問：「CVE-2024-1234 怎麼修？」
```

"CVE-2024-1234" 是精確的識別碼，向量搜尋可能找到「類似漏洞描述」而不是「這個特定 CVE」。
關鍵字搜尋反而更精準。

**這個專案的做法**：`supabase/functions.sql` 的 `match_private_knowledge` 同時跑兩種搜尋再用 RRF 融合——Ch 04 會仔細看這個函式。

---

## 🎯 本章里程碑

能向別人解釋：
```
「LIKE 找字面，向量搜尋找語意。
  同樣的意思換個說法，向量搜尋能找到，LIKE 找不到。」
```

下一章 → [Ch 02：schema.sql 解剖](ch02-schema-deep-dive.md)
