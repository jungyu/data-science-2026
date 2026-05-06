"""ch09 Step 3 — 觸發 project-linebot-rag-skills 的 IngestionPipeline。

從 crawler.articles 讀取已爬文章，交給 linebot-rag-skills 進行：
  chunk → embed（呼叫 Embedding API）→ upsert 到 private_knowledge

兩個模式：
  --dry-run（預設）  只印出要執行的指令，不實際執行
  --run              實際執行，需確認 linebot 專案路徑與環境正確

執行：
    # 預覽指令（安全，不動資料）
    python ch09-rag-bridge/03_trigger_ingest.py --category nextjs

    # 實際執行
    python ch09-rag-bridge/03_trigger_ingest.py --category nextjs --run

    # 只取最近 7 天的新文章
    python ch09-rag-bridge/03_trigger_ingest.py --category nextjs --since 2026-05-01 --run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# linebot-rag-skills 專案預設位於同層目錄
DEFAULT_LINEBOT_PATH = PROJECT_ROOT.parent / "project-linebot-rag-skills"


def find_linebot_root() -> Path | None:
    """偵測 project-linebot-rag-skills 的路徑。"""
    candidate = DEFAULT_LINEBOT_PATH
    if (candidate / "scripts" / "ingest.py").exists():
        return candidate

    env_path = Path(sys.argv[0]).parent  # fallback
    for parent in [PROJECT_ROOT.parent, PROJECT_ROOT.parent.parent]:
        for name in ["project-linebot-rag-skills", "linebot-rag-skills"]:
            p = parent / name
            if (p / "scripts" / "ingest.py").exists():
                return p
    return None


def build_command(linebot_root: Path, args: argparse.Namespace) -> list[str]:
    python = linebot_root / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)  # 降級使用目前 interpreter

    cmd = [str(python), str(linebot_root / "scripts" / "ingest.py"), "articles"]
    if args.category:
        cmd += ["--category", args.category]
    if args.since:
        cmd += ["--since", args.since]
    if args.limit != 500:
        cmd += ["--limit", str(args.limit)]
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(description="觸發 linebot-rag-skills IngestionPipeline")
    parser.add_argument("--category", default=None, help="只處理指定分類")
    parser.add_argument("--since", default=None, metavar="YYYY-MM-DD",
                        help="只取此日期之後新增的文章")
    parser.add_argument("--limit", type=int, default=500, help="最多處理幾篇（預設 500）")
    parser.add_argument("--linebot-path", default=None,
                        help=f"linebot-rag-skills 專案路徑（預設自動偵測）")
    parser.add_argument("--run", action="store_true",
                        help="實際執行（預設只印指令）")
    args = parser.parse_args()

    linebot_root = Path(args.linebot_path) if args.linebot_path else find_linebot_root()

    if linebot_root is None:
        print("❌  找不到 project-linebot-rag-skills 專案目錄。")
        print(f"   預設尋找路徑：{DEFAULT_LINEBOT_PATH}")
        print("   請用 --linebot-path /path/to/project-linebot-rag-skills 手動指定。")
        sys.exit(1)

    print(f"✅  linebot-rag-skills 路徑：{linebot_root}")

    cmd = build_command(linebot_root, args)
    cmd_str = " ".join(cmd)

    print()
    print("─" * 60)
    print("  IngestionPipeline 執行指令：")
    print()
    print(f"    {cmd_str}")
    print()
    print("  效果：crawler.articles → chunk → embed → private_knowledge")
    print("  content_hash 相同的文章會自動跳過（unchanged 計數增加）。")
    print("─" * 60)

    if not args.run:
        print()
        print("  ℹ️  dry-run 模式：加上 --run 才會實際執行。")
        return

    print()
    print("▶️  開始執行 ...")
    result = subprocess.run(cmd, cwd=str(linebot_root))
    if result.returncode == 0:
        print("\n✅  IngestionPipeline 完成。")
        print("   可執行 04_end_to_end_demo.py 做最終驗收。")
    else:
        print(f"\n❌  執行失敗（exit code {result.returncode}）")
        print("   常見原因：")
        print("   1. linebot-rag-skills 的 .env 未設定 SUPABASE_URL / OPENAI_API_KEY")
        print("   2. .venv 未建立（執行 uv sync）")
        print("   3. --category 指定的分類在 crawler.articles 中無資料")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
