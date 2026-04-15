#!/usr/bin/env python3
"""
Embed TCM knowledge atoms into PostgreSQL pgvector column.

Responsibilities:
1. Fetch atoms whose embedding is NULL
2. Generate embeddings from embedding_text
3. Write vectors back to knowledge_atoms.embedding

Environment variables:
  DATABASE_URL               - required
  OPENAI_API_KEY             - required
  OPENAI_EMBEDDING_MODEL     - optional (default: text-embedding-3-small)
  EMBEDDING_BATCH_SIZE       - optional (default: 20)
  EMBEDDING_DRY_RUN          - optional (default: false)
  EMBEDDING_ONLY_ACTIVE      - optional (default: true)
  EMBEDDING_SLEEP_SECONDS    - optional (default: 0.5)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Sequence

import psycopg
from openai import OpenAI

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("embed_atoms")


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    database_url: str
    openai_api_key: str
    embedding_model: str
    batch_size: int
    dry_run: bool
    only_active: bool
    sleep_seconds_between_batches: float


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not database_url:
        raise ValueError("Missing required environment variable: DATABASE_URL")
    if not openai_api_key:
        raise ValueError("Missing required environment variable: OPENAI_API_KEY")

    return Settings(
        database_url=database_url,
        openai_api_key=openai_api_key,
        embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ).strip(),
        batch_size=_get_int("EMBEDDING_BATCH_SIZE", 20),
        dry_run=_get_bool("EMBEDDING_DRY_RUN", False),
        only_active=_get_bool("EMBEDDING_ONLY_ACTIVE", True),
        sleep_seconds_between_batches=float(
            os.getenv("EMBEDDING_SLEEP_SECONDS", "0.5").strip()
        ),
    )


# ---------------------------------------------------------
# Data types
# ---------------------------------------------------------

@dataclass
class AtomRow:
    id: str
    atom_type: str
    canonical_name: str
    embedding_text: str


# ---------------------------------------------------------
# Database helpers
# ---------------------------------------------------------

def fetch_atoms_without_embedding(
    conn: psycopg.Connection,
    limit: int,
    only_active: bool,
) -> list[AtomRow]:
    where_clauses = [
        "embedding IS NULL",
        "embedding_text IS NOT NULL",
        "btrim(embedding_text) <> ''",
    ]

    if only_active:
        where_clauses.append("is_active = true")

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT id, atom_type, canonical_name, embedding_text
        FROM public.knowledge_atoms
        WHERE {where_sql}
        ORDER BY created_at ASC
        LIMIT %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (limit,))
        rows = cur.fetchall()

    return [
        AtomRow(
            id=row[0],
            atom_type=row[1],
            canonical_name=row[2],
            embedding_text=row[3],
        )
        for row in rows
    ]


def update_atom_embedding(
    conn: psycopg.Connection,
    atom_id: str,
    embedding: Sequence[float],
) -> None:
    # pgvector accepts '[1.0, 2.0, ...]' text literal
    vector_literal = json.dumps(list(embedding), ensure_ascii=False)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.knowledge_atoms
            SET embedding = %s::vector
            WHERE id = %s
            """,
            (vector_literal, atom_id),
        )


def count_remaining_atoms(
    conn: psycopg.Connection,
    only_active: bool,
) -> int:
    where_clauses = [
        "embedding IS NULL",
        "embedding_text IS NOT NULL",
        "btrim(embedding_text) <> ''",
    ]

    if only_active:
        where_clauses.append("is_active = true")

    where_sql = " AND ".join(where_clauses)

    sql = f"SELECT count(*) FROM public.knowledge_atoms WHERE {where_sql}"

    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    return int(row[0])


# ---------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------

def build_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def generate_embeddings(
    client: OpenAI,
    model: str,
    texts: Sequence[str],
) -> list[list[float]]:
    response = client.embeddings.create(
        model=model,
        input=list(texts),
    )
    return [item.embedding for item in response.data]


# ---------------------------------------------------------
# Main workflow
# ---------------------------------------------------------

def process_batch(
    conn: psycopg.Connection,
    client: OpenAI,
    settings: Settings,
) -> int:
    atoms = fetch_atoms_without_embedding(
        conn=conn,
        limit=settings.batch_size,
        only_active=settings.only_active,
    )

    if not atoms:
        return 0

    logger.info("Fetched %s atoms for embedding.", len(atoms))

    texts = [atom.embedding_text for atom in atoms]
    embeddings = generate_embeddings(
        client=client,
        model=settings.embedding_model,
        texts=texts,
    )

    if len(embeddings) != len(atoms):
        raise RuntimeError(
            f"Embedding count mismatch: atoms={len(atoms)}, embeddings={len(embeddings)}"
        )

    if settings.dry_run:
        for atom in atoms:
            logger.info(
                "[DRY RUN] Would embed atom id=%s type=%s name=%s",
                atom.id,
                atom.atom_type,
                atom.canonical_name,
            )
        return len(atoms)

    for atom, embedding in zip(atoms, embeddings):
        update_atom_embedding(
            conn=conn,
            atom_id=atom.id,
            embedding=embedding,
        )
        logger.info(
            "Updated embedding for atom id=%s type=%s name=%s",
            atom.id,
            atom.atom_type,
            atom.canonical_name,
        )

    conn.commit()
    return len(atoms)


def run() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        logger.error("Failed to load settings: %s", exc)
        return 1

    logger.info("Embedding model: %s", settings.embedding_model)
    logger.info("Batch size: %s", settings.batch_size)
    logger.info("Dry run: %s", settings.dry_run)
    logger.info("Only active atoms: %s", settings.only_active)

    client = build_openai_client(settings.openai_api_key)

    try:
        with psycopg.connect(settings.database_url) as conn:
            conn.autocommit = False

            remaining_before = count_remaining_atoms(
                conn=conn,
                only_active=settings.only_active,
            )
            logger.info("Atoms without embedding before run: %s", remaining_before)

            if remaining_before == 0:
                logger.info("Nothing to embed. Exiting.")
                return 0

            total_processed = 0

            while True:
                try:
                    processed = process_batch(
                        conn=conn,
                        client=client,
                        settings=settings,
                    )
                except Exception as exc:
                    conn.rollback()
                    logger.error("Batch failed, rolling back: %s", exc)
                    return 1

                if processed == 0:
                    break

                total_processed += processed
                logger.info(
                    "Batch done. Processed this batch: %s | Total so far: %s",
                    processed,
                    total_processed,
                )

                if settings.sleep_seconds_between_batches > 0:
                    time.sleep(settings.sleep_seconds_between_batches)

            remaining_after = count_remaining_atoms(
                conn=conn,
                only_active=settings.only_active,
            )
            logger.info(
                "Run complete. Total processed: %s | Remaining: %s",
                total_processed,
                remaining_after,
            )

    except psycopg.OperationalError as exc:
        logger.error("Database connection error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run())
