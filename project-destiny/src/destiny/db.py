from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector

from destiny.config import Settings


@contextmanager
def connect(settings: Settings) -> Iterator[psycopg.Connection]:
    with psycopg.connect(settings.database_url, autocommit=False) as conn:
        register_vector(conn)
        yield conn
