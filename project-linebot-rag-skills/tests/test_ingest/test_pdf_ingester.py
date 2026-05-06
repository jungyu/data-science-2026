"""PdfIngester 測試 — 用 monkeypatch 替換 pdfplumber.open。

對應 task-25 步驟 11。實機要產 fixture PDF 太複雜；改 mock pdfplumber 供 unit test。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

import pytest

from app.ingest.ingesters import PdfIngester


@dataclass
class _MockPage:
    text: str

    def extract_text(self) -> str:
        return self.text


class _MockPdf:
    def __init__(self, page_texts: list[str]) -> None:
        self.pages = [_MockPage(t) for t in page_texts]


@contextmanager
def _open_factory(page_texts):
    yield _MockPdf(page_texts)


@pytest.mark.asyncio
async def test_yields_one_section_per_page(monkeypatch, tmp_path):
    # 建空 PDF 檔（內容無關，因為 pdfplumber 被 mock）
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")  # 假內容

    # mock pdfplumber.open
    import pdfplumber

    def fake_open(path):
        return _open_factory(["page 1 content", "page 2 content", "page 3 content"])

    monkeypatch.setattr(pdfplumber, "open", fake_open)

    ingester = PdfIngester([pdf], category="regulations")
    docs = [d async for d in ingester.yield_documents()]
    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_type == "pdf"
    assert doc.title == "sample"
    assert len(doc.sections) == 3
    # 每 section 帶 page_number
    assert [s.page_number for s in doc.sections] == [1, 2, 3]
    assert doc.sections[1].text == "page 2 content"
    assert doc.metadata["pages"] == 3


@pytest.mark.asyncio
async def test_skips_empty_pages(monkeypatch, tmp_path):
    pdf = tmp_path / "sparse.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    import pdfplumber

    def fake_open(path):
        # page 2 空（掃描頁未 OCR）
        return _open_factory(["page 1 content", "", "page 3 content"])

    monkeypatch.setattr(pdfplumber, "open", fake_open)

    ingester = PdfIngester([pdf], category="x")
    docs = [d async for d in ingester.yield_documents()]
    assert len(docs[0].sections) == 2
    assert [s.page_number for s in docs[0].sections] == [1, 3]


@pytest.mark.asyncio
async def test_no_extractable_text_yields_nothing(monkeypatch, tmp_path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    import pdfplumber

    def fake_open(path):
        return _open_factory(["", "", ""])

    monkeypatch.setattr(pdfplumber, "open", fake_open)

    ingester = PdfIngester([pdf], category="x")
    docs = [d async for d in ingester.yield_documents()]
    assert docs == []


@pytest.mark.asyncio
async def test_source_url_uses_file_scheme(monkeypatch, tmp_path):
    pdf = tmp_path / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    import pdfplumber

    monkeypatch.setattr(pdfplumber, "open", lambda p: _open_factory(["content"]))

    docs = [d async for d in PdfIngester([pdf], category="x").yield_documents()]
    assert docs[0].source_url.startswith("file://")
    assert "spec.pdf" in docs[0].source_url
