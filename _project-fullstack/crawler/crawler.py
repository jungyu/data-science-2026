"""
Crawler Service — 網頁爬蟲 + ETL Pipeline

功能：
  1. 用 Playwright 抓取網頁純文字內容
  2. 依 token 數切分成小塊（chunking）
  3. 呼叫 OpenAI Embedding API 嵌入向量
  4. 存入 Qdrant 向量資料庫

API 端點：
  POST /crawl           → 爬一個 URL，存進 Qdrant
  POST /crawl/text      → 直接貼文字（不需要網頁），存進 Qdrant
  GET  /collections     → 列出 Qdrant 中的所有 collection
  DELETE /collection/{name} → 刪除整個 collection（重置用）
  GET  /health          → 健康檢查

啟動方式：
  python crawler.py              （開發用）
  docker compose up -d crawler   （Docker 環境）
"""

import os
import re
import uuid

import tiktoken
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
from playwright.async_api import async_playwright
from pydantic import BaseModel, HttpUrl
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

# ── 環境變數 ─────────────────────────────────────────────────
QDRANT_URL     = os.getenv("QDRANT_URL",     "http://localhost:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM   = 1536   # text-embedding-3-small 的向量維度
CHUNK_TOKENS    = 400    # 每塊目標 token 數
CHUNK_OVERLAP   = 50     # 塊間重疊 token 數

# ── 用戶端 ──────────────────────────────────────────────────
openai_client = OpenAI(api_key=OPENAI_API_KEY)
qdrant_client = QdrantClient(url=QDRANT_URL)
tokenizer     = tiktoken.get_encoding("cl100k_base")

app = FastAPI(title="DS Crawler Service")


# ════════════════════════════════════════════════════════════
#  核心函式
# ════════════════════════════════════════════════════════════

async def fetch_page_text(url: str) -> str:
    """用 Playwright 抓取網頁，回傳純文字（去除 script/style 標籤）。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            # 取得 body 純文字（自動去除 HTML tag）
            text = await page.inner_text("body")
        finally:
            await browser.close()

    # 清理：多個空白壓成一個，去頭尾空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, source: str) -> list[dict]:
    """
    把長文字切成帶有 overlap 的小塊。

    回傳格式：
    [
      {"text": "...", "source": "...", "chunk_index": 0},
      ...
    ]
    """
    tokens = tokenizer.encode(text)
    chunks = []
    start  = 0

    while start < len(tokens):
        end        = min(start + CHUNK_TOKENS, len(tokens))
        chunk_text = tokenizer.decode(tokens[start:end])
        chunks.append({
            "text":        chunk_text,
            "source":      source,
            "chunk_index": len(chunks),
        })
        if end == len(tokens):
            break
        start = end - CHUNK_OVERLAP  # 往回 overlap，確保語意連續

    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """批次呼叫 OpenAI Embedding API，把向量加回 chunk dict。"""
    texts = [c["text"] for c in chunks]

    # OpenAI 支援批次送出（最多 2048 個），這裡一次全送
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    for chunk, embedding_data in zip(chunks, response.data):
        chunk["vector"] = embedding_data.embedding

    return chunks


def ensure_collection(collection: str) -> None:
    """確保 Qdrant collection 存在，不存在就建立。"""
    existing = [c.name for c in qdrant_client.get_collections().collections]
    if collection not in existing:
        qdrant_client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )


def upsert_chunks(chunks: list[dict], collection: str) -> int:
    """把已嵌入的 chunks 存進 Qdrant，回傳存入筆數。"""
    ensure_collection(collection)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=chunk["vector"],
            payload={
                "text":        chunk["text"],
                "source":      chunk["source"],
                "chunk_index": chunk["chunk_index"],
            },
        )
        for chunk in chunks
    ]

    qdrant_client.upsert(collection_name=collection, points=points)
    return len(points)


# ════════════════════════════════════════════════════════════
#  API 端點
# ════════════════════════════════════════════════════════════

class CrawlRequest(BaseModel):
    url:        HttpUrl
    collection: str = "knowledge"  # 存入哪個 Qdrant collection


class TextRequest(BaseModel):
    text:       str
    source:     str = "manual"     # 來源標籤（顯示在搜尋結果）
    collection: str = "knowledge"


@app.post("/crawl")
async def crawl_url(req: CrawlRequest):
    """爬取指定 URL，切塊、嵌入後存進 Qdrant。"""
    url_str = str(req.url)

    try:
        # Step 1：抓網頁
        text = await fetch_page_text(url_str)
        if len(text) < 50:
            raise HTTPException(status_code=422, detail="網頁內容太短，可能需要登入或是 JS 渲染頁面")

        # Step 2：切塊
        chunks = chunk_text(text, source=url_str)

        # Step 3：嵌入
        chunks = embed_chunks(chunks)

        # Step 4：存入 Qdrant
        count = upsert_chunks(chunks, req.collection)

        return {
            "status":     "ok",
            "url":        url_str,
            "collection": req.collection,
            "chunks":     count,
            "chars":      len(text),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/crawl/text")
async def crawl_text(req: TextRequest):
    """直接把文字存進 Qdrant（不需要爬網頁，適合貼上 PDF 內容或自訂文字）。"""
    if len(req.text.strip()) < 10:
        raise HTTPException(status_code=422, detail="文字太短")

    try:
        chunks = chunk_text(req.text, source=req.source)
        chunks = embed_chunks(chunks)
        count  = upsert_chunks(chunks, req.collection)

        return {
            "status":     "ok",
            "source":     req.source,
            "collection": req.collection,
            "chunks":     count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections")
def list_collections():
    """列出 Qdrant 中的所有 collection 及每個 collection 的點數。"""
    collections = qdrant_client.get_collections().collections
    result = []
    for c in collections:
        info  = qdrant_client.get_collection(c.name)
        result.append({
            "name":   c.name,
            "points": info.points_count,
        })
    return {"collections": result}


@app.delete("/collection/{name}")
def delete_collection(name: str):
    """刪除整個 collection（重置知識庫用）。"""
    existing = [c.name for c in qdrant_client.get_collections().collections]
    if name not in existing:
        raise HTTPException(status_code=404, detail=f"Collection [{name}] 不存在")
    qdrant_client.delete_collection(name)
    return {"status": "deleted", "collection": name}


@app.get("/health")
def health():
    try:
        collections = qdrant_client.get_collections().collections
        qdrant_ok   = True
    except Exception:
        collections = []
        qdrant_ok   = False

    return {
        "status":      "ok",
        "qdrant":      QDRANT_URL,
        "qdrant_ok":   qdrant_ok,
        "collections": [c.name for c in collections],
    }


# ── 啟動 ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Crawler Service 啟動中（port 3001）")
    print("  POST /crawl        → 爬網頁 → Qdrant")
    print("  POST /crawl/text   → 貼文字 → Qdrant")
    print("  GET  /collections  → 列出知識庫")
    print("  GET  /health       → 健康檢查")
    uvicorn.run(app, host="0.0.0.0", port=3001)
