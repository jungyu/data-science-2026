"""CsvIngester 測試。對應 task-25 步驟 11。"""

from __future__ import annotations

import pytest

from app.ingest.ingesters import CsvIngester, CsvIngesterConfig


def _write_csv(tmp_path, rows: list[dict], *, name: str = "faq.csv") -> str:
    import csv as csv_module

    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv_module.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


@pytest.mark.asyncio
async def test_row_per_doc_yields_one_doc_per_row(tmp_path):
    path = _write_csv(tmp_path, [
        {"question": "什麼是 RAG", "answer": "檢索增強生成", "topic": "intro"},
        {"question": "向量檢索原理", "answer": "用 embedding 比相似度", "topic": "vector"},
    ])
    cfg = CsvIngesterConfig(
        path=path, mode="row_per_doc",
        text_columns=["question", "answer"],
        metadata_columns=["topic"],
        title_column="question",
    )
    ingester = CsvIngester(cfg, category="faq")

    docs = [d async for d in ingester.yield_documents()]
    assert len(docs) == 2
    assert docs[0].title == "什麼是 RAG"
    assert "RAG" in docs[0].sections[0].text
    assert "檢索增強生成" in docs[0].sections[0].text
    assert docs[0].sections[0].metadata["topic"] == "intro"


@pytest.mark.asyncio
async def test_row_per_doc_skips_empty_rows(tmp_path):
    path = _write_csv(tmp_path, [
        {"question": "Q1", "answer": "A1"},
        {"question": "", "answer": ""},
        {"question": "Q2", "answer": "A2"},
    ])
    cfg = CsvIngesterConfig(path=path, mode="row_per_doc", text_columns=["question", "answer"])
    docs = [d async for d in CsvIngester(cfg, category="faq").yield_documents()]
    assert len(docs) == 2  # 空列被跳過


@pytest.mark.asyncio
async def test_table_as_doc_combines_rows(tmp_path):
    path = _write_csv(tmp_path, [
        {"sku": "A1", "name": "alpha"},
        {"sku": "B2", "name": "beta"},
    ])
    cfg = CsvIngesterConfig(
        path=path, mode="table_as_doc", text_columns=["sku", "name"]
    )
    docs = [d async for d in CsvIngester(cfg, category="catalog").yield_documents()]
    assert len(docs) == 1
    assert "A1" in docs[0].sections[0].text
    assert "beta" in docs[0].sections[0].text
    assert docs[0].metadata["row_count"] == 2


@pytest.mark.asyncio
async def test_title_template_used_when_no_title_column(tmp_path):
    path = _write_csv(tmp_path, [
        {"question": "Q1", "answer": "A1"},
    ])
    cfg = CsvIngesterConfig(
        path=path, mode="row_per_doc",
        text_columns=["question", "answer"],
        title_template="FAQ: {question}",
    )
    docs = [d async for d in CsvIngester(cfg, category="faq").yield_documents()]
    assert docs[0].title == "FAQ: Q1"


@pytest.mark.asyncio
async def test_text_columns_default_to_all(tmp_path):
    path = _write_csv(tmp_path, [
        {"a": "alpha", "b": "beta"},
    ])
    # 沒指定 text_columns → 所有欄位
    cfg = CsvIngesterConfig(path=path, mode="row_per_doc")
    docs = [d async for d in CsvIngester(cfg, category="x").yield_documents()]
    text = docs[0].sections[0].text
    assert "alpha" in text and "beta" in text
