"""HITL review queue CLI — 對應 spec-21 / task-21 步驟 6。

用法：

    python scripts/review_queue.py list
    python scripts/review_queue.py show <thread_id>
    python scripts/review_queue.py approve <thread_id>
    python scripts/review_queue.py revise <thread_id> --text "改後內容"
    python scripts/review_queue.py drop <thread_id>

說明：
- `list` 用 graph 的 checkpointer 列出 next=human_review 的 thread
- approve / revise / drop 用 update_state + ainvoke(None) resume graph
- 需 services.checkpointer 存活（SqliteSaver 需 FastAPI 跨程序共用，
  教學版用 memory backend 在同一 process 內展示）
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.dependencies import get_runtime_services


def _cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _list_pending(services) -> list[dict]:
    """用 checkpointer 列出 next=human_review 的 thread。"""
    cp = services.checkpointer
    if cp is None:
        return []
    out: list[dict] = []
    # checkpointer.list 回傳所有 thread 的 latest checkpoint
    for tup in cp.list(None, limit=200):
        cfg = tup.config
        thread_id = cfg["configurable"].get("thread_id")
        if not thread_id:
            continue
        snapshot = services.rag_graph.get_state(_cfg(thread_id))
        if "human_review" in (snapshot.next or ()):
            v = snapshot.values
            out.append({
                "thread_id": thread_id,
                "external_user_id": v.get("external_user_id"),
                "query": v.get("user_input", "")[:80],
                "judge_mean": (
                    v["judge_score"].mean if v.get("judge_score") else None
                ),
            })
    return out


def cmd_list(services) -> None:
    rows = _list_pending(services)
    if not rows:
        print("(no pending reviews)")
        return
    print(f"{'thread_id':<40} {'user':<20} {'judge_mean':>10}  query")
    print("-" * 100)
    for r in rows:
        mean = f"{r['judge_mean']:.1f}" if r["judge_mean"] is not None else "—"
        print(f"{r['thread_id']:<40} {r['external_user_id'] or '?':<20} {mean:>10}  {r['query']}")


def cmd_show(services, thread_id: str) -> None:
    snapshot = services.rag_graph.get_state(_cfg(thread_id))
    if not snapshot.values:
        print(f"no state for thread {thread_id}")
        return
    v = snapshot.values
    print(f"thread:    {thread_id}")
    print(f"user:      {v.get('external_user_id')}")
    print(f"query:     {v.get('user_input')}")
    contract = v.get("answer_contract")
    if contract is not None:
        print(f"contract.summary: {contract.summary}")
        print(f"contract.findings: {len(contract.key_findings)}")
        print(f"contract.citations: {len(contract.citations)}")
    score = v.get("judge_score")
    if score is not None:
        print(
            f"judge: ground={score.groundedness} cite={score.citation_fidelity} "
            f"format={score.format_completeness} uncert={score.uncertainty_honesty} "
            f"mean={score.mean:.1f}"
        )
        print(f"judge.issues: {score.issues}")
    print("\nnarrative:")
    for r in v.get("responses") or []:
        print("  " + r.replace("\n", "\n  "))
    print(f"\nnext: {snapshot.next}")


async def _resume(services, thread_id: str, decision: str, **extra) -> None:
    cfg = _cfg(thread_id)
    update = {
        "reviewer_decision": decision,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    services.rag_graph.update_state(cfg, update)
    await services.rag_graph.ainvoke(None, config=cfg)
    print(f"resumed thread {thread_id} with decision={decision}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("show"); p.add_argument("thread_id")
    p = sub.add_parser("approve"); p.add_argument("thread_id")
    p = sub.add_parser("revise"); p.add_argument("thread_id"); p.add_argument("--text", required=True)
    p = sub.add_parser("drop"); p.add_argument("thread_id")
    args = parser.parse_args()

    services = get_runtime_services()

    if args.cmd == "list":
        cmd_list(services)
    elif args.cmd == "show":
        cmd_show(services, args.thread_id)
    elif args.cmd == "approve":
        asyncio.run(_resume(services, args.thread_id, "approve"))
    elif args.cmd == "revise":
        asyncio.run(_resume(services, args.thread_id, "revise", reviewer_revised_text=args.text))
    elif args.cmd == "drop":
        asyncio.run(_resume(services, args.thread_id, "drop"))


if __name__ == "__main__":
    main()
