# Spec-07：Notion Ingestion

> **✅ 已修補 ImportError（commit `2387555`）；UUID/連結清理仍為已知 gap**
>
> - 原本 `scripts/ingest_notion_export.py` import 不存在的 `ingest_path` 直接 ImportError，現已重寫
> - 新版支援 dir 與 `.zip` 兩種輸入；走 `IngestionPipeline + MarkdownIngester`
> - 不打 Notion API；走 API 路徑請看 [spec-25](./spec-25-multi-format-ingestion.md) 的 `NotionIngester`
> - Notion UUID 後綴清理、內部連結轉換、metadata block 移除仍未實作（屬於後續優化）

## 背景

`scripts/ingest_notion_export.py` 目前只是掃描 `.md` 檔案並呼叫通用的 Markdown ingestion，沒有 Notion 特定的邏輯。Notion Export 的 ZIP 包含特定的資料夾結構與 `.md` 格式（含 Notion ID 後綴、資料庫頁面等），需要特別處理。

## 目標

讓 `ingest_notion_export.py` 能接收 Notion 匯出的 ZIP 檔案，正確解析並匯入到知識庫。

## Notion Export 格式特性

Notion 匯出的 ZIP 包含：
- 頁面：`PageName abc123def456.md`（檔名含 Notion UUID）
- 資料庫：`DatabaseName abc123def456/` 資料夾，內含多個頁面 `.md`
- 圖片：`image.png`（匯入時忽略）
- 內嵌連結：`[text](PageName%20abc123.md)`（本地連結，需轉換或忽略）

## 介面

```bash
.venv/bin/python scripts/ingest_notion_export.py \
  --zip path/to/notion-export.zip \
  --category notes \
  [--prefix "Notion/"]   # 可選，加在 title 前綴以便識別來源
```

## 實作要點

1. **解壓縮 ZIP** 到 temp 目錄
2. **遞迴掃描** `.md` 檔案，跳過圖片與 CSV
3. **清理 Notion 特有格式**：
   - 移除 Notion UUID 後綴（`PageName abc123def456.md` → title 為 `PageName`）
   - 移除 Notion 內部連結（`[text](./xxx.md)` → 保留文字，移除連結）
   - 移除 Notion metadata block（`Created: ...`、`Tags: ...` 等開頭的屬性行）
4. **Chunking**：與現有 `chunker.py` 共用邏輯
5. **Upsert**：與現有 `ingest_markdown.py` 共用邏輯（`content_hash` 去重）
6. **清理** temp 目錄

## 介面契約

**修改**：`scripts/ingest_notion_export.py`

```python
def clean_notion_title(filename: str) -> str:
    # "PageName abc123def456.md" → "PageName"
    return re.sub(r'\s+[0-9a-f]{32}(\.md)?$', '', filename.stem)

def clean_notion_content(content: str) -> str:
    # 移除 Notion metadata block、內部連結
    ...

async def ingest_notion_zip(zip_path: Path, category: str, prefix: str = "") -> int:
    # 回傳成功匯入的 chunk 數
    ...
```

## 不做什麼

- 不使用 Notion API（用 Export ZIP，不需要 token）
- 不解析 Notion Database 的 property（只取頁面文字內容）
- 不匯入圖片

## 驗收標準

- `ingest_notion_export.py --zip test.zip --category notes` 執行後無錯誤
- `private_knowledge` 有新記錄，title 不含 Notion UUID
- 能查詢匯入的 Notion 頁面內容
- 空 ZIP 或無 `.md` 檔案時，印出警告並正常結束（不拋錯）
