# task-07：實作 Notion Export Ingestion

> 規格詳見 [spec-07](../specs/spec-07-notion-ingestion.md)
>
> **✅ 已完成（commit `2387555`）** — 實作記錄與驗收測試見 spec-07 頂部「實作狀態」段。
---

請重寫 `scripts/ingest_notion_export.py`，讓它能正確處理 Notion Export ZIP 格式。

## 使用方式（完成後）

```bash
.venv/bin/python scripts/ingest_notion_export.py \
  --zip ~/Downloads/notion-export.zip \
  --category notes \
  [--prefix "Notion/"]
```

## 實作要求

### 1. 解壓縮 ZIP

```python
import zipfile, tempfile, shutil
from pathlib import Path

def extract_zip(zip_path: Path) -> Path:
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp)
    return tmp   # 呼叫方負責 shutil.rmtree(tmp)
```

### 2. 清理 Notion 檔名（取得 title）

```python
import re

def clean_notion_title(stem: str) -> str:
    # "My Page abc123def456789012345678901234" → "My Page"
    return re.sub(r'\s+[0-9a-f]{32}$', '', stem).strip()
```

### 3. 清理 Notion 內容

```python
def clean_notion_content(content: str) -> str:
    lines = content.splitlines()
    cleaned = []
    skip_header = True
    for line in lines:
        # 跳過開頭的 Notion metadata block（連續的 "Key: value" 行）
        if skip_header and re.match(r'^[A-Za-z一-鿿]+:\s', line):
            continue
        skip_header = False
        # 移除本地連結（保留連結文字）
        line = re.sub(r'\[([^\]]+)\]\([^)]+\.md[^)]*\)', r'\1', line)
        cleaned.append(line)
    return '\n'.join(cleaned).strip()
```

### 4. 主流程

```python
async def ingest_notion_zip(zip_path: Path, category: str, prefix: str = "") -> int:
    tmp = extract_zip(zip_path)
    try:
        md_files = list(tmp.rglob("*.md"))
        if not md_files:
            print("No .md files found in ZIP")
            return 0
        total = 0
        for md_file in md_files:
            title = (prefix + clean_notion_title(md_file.stem)) or md_file.name
            content = clean_notion_content(md_file.read_text(encoding="utf-8"))
            if not content:
                continue
            # 呼叫現有的 chunk + embed + upsert 邏輯
            n = await ingest_text(content, title=title, category=category, source_id=str(md_file))
            total += n
        print(f"Ingested {total} chunks from {len(md_files)} Notion pages")
        return total
    finally:
        shutil.rmtree(tmp)
```

### 5. 共用 `ingest_text()` 

將 `ingest_markdown.py` 的核心 chunk + embed + upsert 邏輯抽取成 `app/rag/ingest.py` 的共用函式，讓兩個腳本都能引用。

## 請輸出

1. `app/rag/ingest.py`（共用的 chunk + embed + upsert 邏輯）
2. 修改後的 `scripts/ingest_markdown.py`（改為引用 `app/rag/ingest`）
3. 重寫後的 `scripts/ingest_notion_export.py`
4. 測試：建立一個小型 mock ZIP，確認 title 清理與 chunk 數量正確

## 驗收指令

```bash
# 建立測試 ZIP
cd /tmp && mkdir notion-test && echo "# 測試頁面\n\n這是內容。" > "notion-test/Test Page abc123def456789012345678901234.md"
cd /tmp && zip -r notion-test.zip notion-test/

.venv/bin/python scripts/ingest_notion_export.py --zip /tmp/notion-test.zip --category notes
# 期望：Ingested N chunks，title 為 "Test Page"（無 UUID）
```
