from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ingest_markdown import ingest_path


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir")
    parser.add_argument("--category", default="notion")
    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    markdown_files = sorted(export_dir.rglob("*.md"))
    total = 0
    for path in markdown_files:
        total += await ingest_path(path, category=args.category)
    print(f"Ingested {total} chunks from {len(markdown_files)} markdown files.")


if __name__ == "__main__":
    asyncio.run(main())
