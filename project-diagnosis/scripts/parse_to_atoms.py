#!/usr/bin/env python3
"""
Parse 醫砭 source_documents (已 scrape, ingestion_status='cleaned')
into knowledge_atoms rows.

Heuristic-based parser targeting《中醫症狀鑒別診斷學》頁面結構：
  - 標題 = symptom canonical_name
  - 「概念」段落 → summary_text
  - 「常見證候」列表 → 產生 (symptom)→(pattern) atom_relations（suggests，低權重）
  - 其餘整段作為 body_markdown 保留

Idempotent:
  - knowledge_atoms.id 固定為 `atm_sym_yibian_{sid}`
  - atom_relations 使用 uq_atom_relations_edge 做 upsert

After running this, call embed_atoms.py to generate vectors.

Environment variables:
  DATABASE_URL         - required
  PARSE_LIMIT          - optional max documents to parse per run (default: 0 = all)
  PARSE_DRY_RUN        - optional (default: false)
"""

from __future__ import annotations

import logging
import os
import re
import sys
import ulid
from dataclasses import dataclass
from typing import Any

import psycopg


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("parse_to_atoms")


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    database_url: str
    parse_limit: int
    dry_run: bool


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("Missing required environment variable: DATABASE_URL")

    return Settings(
        database_url=database_url,
        parse_limit=int(os.getenv("PARSE_LIMIT", "0")),
        dry_run=os.getenv("PARSE_DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"},
    )


# ---------------------------------------------------------
# Parsing
# ---------------------------------------------------------

SECTION_HEADINGS = {
    "概念": "concept",
    "常見證候": "common_patterns",
    "鑑別分析": "differential",
    "文獻別錄": "citations",
}

PATTERN_TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,12}證?")


@dataclass
class ParsedSections:
    concept: str | None
    common_patterns: list[str]
    body_markdown: str


def split_sections(markdown: str) -> dict[str, str]:
    """Split markdown by ## / ### headings into section-name → text."""
    lines = markdown.splitlines()
    sections: dict[str, str] = {}
    current_name = "_preamble"
    buffer: list[str] = []

    heading_re = re.compile(r"^#{2,4}\s+(.+?)\s*$")

    for line in lines:
        match = heading_re.match(line)
        if match:
            if buffer:
                sections[current_name] = "\n".join(buffer).strip()
            current_name = match.group(1).strip()
            buffer = []
        else:
            buffer.append(line)

    if buffer:
        sections[current_name] = "\n".join(buffer).strip()

    return sections


def extract_pattern_candidates(text: str) -> list[str]:
    """Extract likely pattern names from a common-patterns section.

    Heuristic: look for bullet items, extract leading phrase before 「：」/「:」 or EOL.
    Filter out short or generic tokens.
    """
    candidates: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[-•・\d\.\s]+", "", line)
        head = re.split(r"[：:]", line, maxsplit=1)[0].strip()
        if not head or len(head) < 2 or len(head) > 20:
            continue
        if not PATTERN_TOKEN_PATTERN.fullmatch(head):
            continue
        candidates.append(head)

    seen: set[str] = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]


def parse_document(title: str, clean_markdown: str) -> ParsedSections:
    sections = split_sections(clean_markdown)

    concept = sections.get("概念")
    pattern_text = sections.get("常見證候", "")
    common_patterns = extract_pattern_candidates(pattern_text)

    return ParsedSections(
        concept=concept,
        common_patterns=common_patterns,
        body_markdown=clean_markdown,
    )


# ---------------------------------------------------------
# Database I/O
# ---------------------------------------------------------

def fetch_unparsed_documents(
    conn: psycopg.Connection,
    limit: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT id, title, clean_markdown, source_url, source_ref, metadata
        FROM public.source_documents
        WHERE source_type = 'html_page'
          AND ingestion_status = 'cleaned'
          AND clean_markdown IS NOT NULL
        ORDER BY created_at ASC
    """
    params: tuple = ()
    if limit > 0:
        sql += " LIMIT %s"
        params = (limit,)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "title": r[1],
            "clean_markdown": r[2],
            "source_url": r[3],
            "source_ref": r[4],
            "metadata": r[5] or {},
        }
        for r in rows
    ]


def upsert_symptom_atom(
    conn: psycopg.Connection,
    source_doc: dict[str, Any],
    parsed: ParsedSections,
) -> str:
    sid = source_doc["source_ref"] or source_doc["id"].replace("src_yibian_", "")
    atom_id = f"atm_sym_yibian_{sid}"

    embedding_text = _build_embedding_text(
        title=source_doc["title"],
        concept=parsed.concept,
        patterns=parsed.common_patterns,
    )

    metadata = {
        "symptom_family": _guess_symptom_family(source_doc["title"], parsed.concept or ""),
        "related_patterns": parsed.common_patterns,
        "source_url": source_doc["source_url"],
        "source_ref": source_doc["source_ref"],
    }

    sql = """
        INSERT INTO public.knowledge_atoms (
          id, source_document_id, atom_type, title, canonical_name, aliases,
          domain, category,
          body_markdown, summary_text, embedding_text,
          authority_level, is_active, metadata
        ) VALUES (
          %(id)s, %(source_document_id)s, 'symptom',
          %(title)s, %(canonical_name)s, '[]'::jsonb,
          '內科症狀', NULL,
          %(body_markdown)s, %(summary_text)s, %(embedding_text)s,
          85, true, %(metadata)s::jsonb
        )
        ON CONFLICT (id) DO UPDATE SET
          source_document_id = EXCLUDED.source_document_id,
          title = EXCLUDED.title,
          canonical_name = EXCLUDED.canonical_name,
          body_markdown = EXCLUDED.body_markdown,
          summary_text = EXCLUDED.summary_text,
          embedding_text = EXCLUDED.embedding_text,
          metadata = EXCLUDED.metadata,
          updated_at = now()
    """

    import json

    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "id": atom_id,
                "source_document_id": source_doc["id"],
                "title": source_doc["title"],
                "canonical_name": source_doc["title"],
                "body_markdown": parsed.body_markdown,
                "summary_text": (parsed.concept or "")[:1000] or None,
                "embedding_text": embedding_text,
                "metadata": json.dumps(metadata, ensure_ascii=False),
            },
        )
    return atom_id


def ensure_pattern_placeholder(
    conn: psycopg.Connection,
    canonical_name: str,
) -> str | None:
    """Return existing pattern atom id by canonical_name, else None.

    We do NOT auto-create pattern atoms here — pattern atoms should come
    from curated seed or L0 教材 ingestion. This keeps relation quality
    high and avoids polluting the ontology with unvetted names.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM public.knowledge_atoms
            WHERE atom_type = 'pattern'
              AND canonical_name = %s
            LIMIT 1
            """,
            (canonical_name,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def upsert_suggests_relation(
    conn: psycopg.Connection,
    symptom_atom_id: str,
    pattern_atom_id: str,
    source_document_id: str,
) -> None:
    rel_id = f"rel_{ulid.new()}"
    sql = """
        INSERT INTO public.atom_relations (
          id, from_atom_id, relation_type, to_atom_id, weight,
          evidence_source_document_id, evidence_note
        ) VALUES (
          %s, %s, 'suggests', %s, 0.50, %s,
          '醫砭《中醫症狀鑒別診斷學》常見證候段落自動抽取'
        )
        ON CONFLICT (from_atom_id, relation_type, to_atom_id) DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql, (rel_id, symptom_atom_id, pattern_atom_id, source_document_id))


def mark_document_parsed(conn: psycopg.Connection, source_document_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.source_documents
            SET ingestion_status = 'parsed', updated_at = now()
            WHERE id = %s
            """,
            (source_document_id,),
        )


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _build_embedding_text(
    title: str,
    concept: str | None,
    patterns: list[str],
) -> str:
    parts = [f"症狀 {title}"]
    if concept:
        parts.append(concept[:400])
    if patterns:
        parts.append("常見證候 " + " ".join(patterns[:10]))
    return " ".join(parts)


_SYMPTOM_FAMILY_HINTS = [
    ("汗", "汗證"),
    ("熱", "發熱"),
    ("寒", "惡寒"),
    ("痛", "疼痛"),
    ("咳", "咳嗽"),
    ("瀉", "泄瀉"),
    ("便", "便症"),
    ("眠", "不寐"),
    ("煩", "神志"),
    ("悸", "心悸"),
]


def _guess_symptom_family(title: str, concept: str) -> str:
    combined = title + concept
    for key, family in _SYMPTOM_FAMILY_HINTS:
        if key in combined:
            return family
    return "其他"


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def run() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        logger.error("Failed to load settings: %s", exc)
        return 1

    logger.info("Parse limit: %s | Dry run: %s", settings.parse_limit or "unlimited", settings.dry_run)

    try:
        with psycopg.connect(settings.database_url) as conn:
            conn.autocommit = False

            docs = fetch_unparsed_documents(conn, settings.parse_limit)
            logger.info("Fetched %s source_documents to parse.", len(docs))

            atoms_created = 0
            relations_created = 0

            for doc in docs:
                try:
                    parsed = parse_document(doc["title"], doc["clean_markdown"])

                    if settings.dry_run:
                        logger.info(
                            "[DRY RUN] %s → concept=%s, patterns=%s",
                            doc["title"],
                            (parsed.concept or "")[:40],
                            parsed.common_patterns,
                        )
                        continue

                    symptom_atom_id = upsert_symptom_atom(conn, doc, parsed)
                    atoms_created += 1

                    for pattern_name in parsed.common_patterns:
                        pattern_atom_id = ensure_pattern_placeholder(conn, pattern_name)
                        if pattern_atom_id is None:
                            logger.debug(
                                "No curated pattern atom for '%s', skipping relation.",
                                pattern_name,
                            )
                            continue
                        upsert_suggests_relation(
                            conn,
                            symptom_atom_id=symptom_atom_id,
                            pattern_atom_id=pattern_atom_id,
                            source_document_id=doc["id"],
                        )
                        relations_created += 1

                    mark_document_parsed(conn, doc["id"])
                    conn.commit()
                    logger.info(
                        "Parsed %s → atom=%s, %s related patterns (%s linked)",
                        doc["title"],
                        symptom_atom_id,
                        len(parsed.common_patterns),
                        sum(
                            1 for p in parsed.common_patterns
                            if ensure_pattern_placeholder(conn, p)
                        ),
                    )
                except Exception as exc:
                    conn.rollback()
                    logger.error("Failed to parse %s: %s", doc["id"], exc)

            logger.info(
                "Parse complete. Atoms upserted: %s | Relations upserted: %s",
                atoms_created,
                relations_created,
            )

    except psycopg.OperationalError as exc:
        logger.error("Database connection error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run())
