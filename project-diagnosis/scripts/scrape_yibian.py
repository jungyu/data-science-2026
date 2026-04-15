#!/usr/bin/env python3
"""
Scrape 醫砭《中醫症狀鑒別診斷學》pages into source_documents.

Target: https://yibian.hopto.org/shu/?cat=dir&sno=6

Responsibilities:
1. Crawl directory pages to collect individual symptom entry URLs
2. Fetch each entry, extract title + body
3. Insert/update source_documents with raw_content and clean_markdown
4. Respect rate limit and robots etiquette

Environment variables:
  DATABASE_URL            - required
  YIBIAN_BASE_URL         - optional (default: https://yibian.hopto.org)
  YIBIAN_ROOT_CAT_SNO     - optional (default: 6)
  YIBIAN_REQUEST_DELAY    - optional seconds between requests (default: 1.5)
  YIBIAN_MAX_PAGES        - optional hard cap on scraped pages (default: 0 = unlimited)
  YIBIAN_USER_AGENT       - optional
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
import ulid
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
import psycopg
from bs4 import BeautifulSoup


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("scrape_yibian")


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    database_url: str
    base_url: str
    root_cat_sno: int
    request_delay: float
    max_pages: int
    user_agent: str


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("Missing required environment variable: DATABASE_URL")

    return Settings(
        database_url=database_url,
        base_url=os.getenv("YIBIAN_BASE_URL", "https://yibian.hopto.org").strip().rstrip("/"),
        root_cat_sno=int(os.getenv("YIBIAN_ROOT_CAT_SNO", "6")),
        request_delay=float(os.getenv("YIBIAN_REQUEST_DELAY", "1.5")),
        max_pages=int(os.getenv("YIBIAN_MAX_PAGES", "0")),
        user_agent=os.getenv(
            "YIBIAN_USER_AGENT",
            "DataslatesTCMResearchBot/0.1 (+research; contact=admin@example.com)",
        ),
    )


# ---------------------------------------------------------
# Data types
# ---------------------------------------------------------

@dataclass
class EntryLink:
    sid: str
    title: str
    url: str


@dataclass
class ParsedEntry:
    sid: str
    title: str
    url: str
    raw_html: str
    clean_markdown: str


# ---------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------

def build_client(settings: Settings) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": settings.user_agent, "Accept-Language": "zh-TW,zh;q=0.9"},
        timeout=30.0,
        follow_redirects=True,
    )


def fetch_html(client: httpx.Client, url: str, delay: float) -> str:
    logger.debug("GET %s", url)
    response = client.get(url)
    response.raise_for_status()
    time.sleep(delay)
    return response.text


# ---------------------------------------------------------
# Parsing
# ---------------------------------------------------------

_SID_PATTERN = re.compile(r"sid=(\d+)")


def collect_entry_links_from_directory(html: str, base_url: str) -> list[EntryLink]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[EntryLink] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "sid=" not in href:
            continue

        absolute_url = urljoin(base_url, href)
        query = parse_qs(urlparse(absolute_url).query)
        sid_values = query.get("sid")
        if not sid_values:
            continue

        sid = sid_values[0]
        title = a.get_text(strip=True)
        if not title:
            continue

        links.append(EntryLink(sid=sid, title=title, url=absolute_url))

    return _dedupe_by_sid(links)


def _dedupe_by_sid(links: Iterable[EntryLink]) -> list[EntryLink]:
    seen: set[str] = set()
    result: list[EntryLink] = []
    for link in links:
        if link.sid in seen:
            continue
        seen.add(link.sid)
        result.append(link)
    return result


def html_to_clean_markdown(html: str, title: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # 醫砭內文常在主要內容區塊
    main = soup.find("div", id="content") or soup.find("div", class_="content") or soup.body or soup

    lines: list[str] = [f"# {title}", ""]

    for node in main.descendants:
        name = getattr(node, "name", None)
        if name in {"h1", "h2", "h3", "h4"}:
            level = int(name[1])
            text = node.get_text(strip=True)
            if text:
                lines.append("")
                lines.append(f"{'#' * level} {text}")
                lines.append("")
        elif name == "p":
            text = node.get_text(strip=True)
            if text:
                lines.append(text)
                lines.append("")
        elif name == "li":
            text = node.get_text(strip=True)
            if text:
                lines.append(f"- {text}")

    markdown = "\n".join(lines)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def upsert_source_document(conn: psycopg.Connection, entry: ParsedEntry) -> str:
    sql = """
        INSERT INTO public.source_documents (
            id, source_type, title, canonical_title,
            authority_level, citation_tier,
            source_url, source_ref, language_code,
            raw_content, clean_markdown,
            metadata, ingestion_status
        )
        VALUES (
            %(id)s, 'html_page', %(title)s, %(title)s,
            85, 'secondary',
            %(url)s, %(sid)s, 'zh-Hant',
            %(raw_html)s, %(clean_markdown)s,
            %(metadata)s::jsonb, 'cleaned'
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            source_url = EXCLUDED.source_url,
            raw_content = EXCLUDED.raw_content,
            clean_markdown = EXCLUDED.clean_markdown,
            metadata = EXCLUDED.metadata,
            ingestion_status = 'cleaned',
            updated_at = now()
        RETURNING id
    """

    metadata_json = f'{{"publisher": "醫砭", "sid": "{entry.sid}"}}'
    doc_id = f"src_yibian_{entry.sid}"

    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "id": doc_id,
                "title": entry.title,
                "url": entry.url,
                "sid": entry.sid,
                "raw_html": entry.raw_html,
                "clean_markdown": entry.clean_markdown,
                "metadata": metadata_json,
            },
        )
        row = cur.fetchone()
    return row[0]


# ---------------------------------------------------------
# Main workflow
# ---------------------------------------------------------

def run() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        logger.error("Failed to load settings: %s", exc)
        return 1

    directory_url = f"{settings.base_url}/shu/?cat=dir&sno={settings.root_cat_sno}&xpd=1"
    logger.info("Directory URL: %s", directory_url)

    with build_client(settings) as client:
        try:
            directory_html = fetch_html(client, directory_url, settings.request_delay)
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch directory: %s", exc)
            return 1

        entries = collect_entry_links_from_directory(directory_html, settings.base_url)
        logger.info("Discovered %s entries in directory", len(entries))

        if settings.max_pages > 0:
            entries = entries[: settings.max_pages]
            logger.info("Capped to %s entries by YIBIAN_MAX_PAGES", len(entries))

        if not entries:
            logger.warning("No entries found. Check selector logic.")
            return 0

        try:
            with psycopg.connect(settings.database_url) as conn:
                conn.autocommit = False

                total = 0
                for idx, link in enumerate(entries, start=1):
                    try:
                        raw = fetch_html(client, link.url, settings.request_delay)
                        markdown = html_to_clean_markdown(raw, link.title)
                        parsed = ParsedEntry(
                            sid=link.sid,
                            title=link.title,
                            url=link.url,
                            raw_html=raw,
                            clean_markdown=markdown,
                        )
                        doc_id = upsert_source_document(conn, parsed)
                        conn.commit()
                        total += 1
                        logger.info(
                            "[%s/%s] Saved %s (sid=%s, title=%s)",
                            idx, len(entries), doc_id, link.sid, link.title,
                        )
                    except Exception as exc:
                        conn.rollback()
                        logger.error(
                            "Failed on sid=%s (%s): %s",
                            link.sid, link.title, exc,
                        )

                logger.info("Scrape complete. Saved %s / %s entries.", total, len(entries))

        except psycopg.OperationalError as exc:
            logger.error("Database connection error: %s", exc)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(run())
