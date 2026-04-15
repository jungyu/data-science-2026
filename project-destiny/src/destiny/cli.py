"""destiny CLI — 目前提供 embedding backfill 與檢索範例。

Usage:
    destiny backfill-embeddings
    destiny query --day-master 甲 --month-branch 申 --pattern 正官格 --text "申月甲木正官格"
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from pathlib import Path

from destiny.bazi_engine import compute_chart
from destiny.config import Settings
from destiny.db import connect
from destiny.embeddings import EmbeddingClient
from destiny.etl import ingest_file
from destiny.evaluation import run_evaluation
from destiny.generation import generate_analysis
from destiny.judge import judge_output
from destiny.retrieval import (
    RetrievalHit,
    RetrievalQuery,
    retrieve,
    retrieve_multi_seed,
)
from destiny.rule_engine import run_rules

if False:  # typing-only import, avoid runtime dep cycle
    from destiny.models import BaziChart, RuleOutput


def _retrieve_for_chart(
    conn, embedder, chart, rules, top_k: int, fusion: str = "max"
) -> list[RetrievalHit]:
    """共用：依 Rule Engine 輸出，以 multi-seed 檢索召回。"""
    if not rules.retrieval_query_seeds:
        return []
    return retrieve_multi_seed(
        conn, embedder,
        seeds=rules.retrieval_query_seeds,
        day_master_tags=[chart.day_master],
        month_branch_tags=[chart.month_commander],
        pattern_tags=[p.pattern for p in rules.candidate_patterns],
        seasonal_tags=[chart.season, *rules.seasonal_adjustment_needed],
        top_k=top_k,
        fusion=fusion,  # type: ignore[arg-type]
    )

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@app.command("backfill-embeddings")
def backfill_embeddings(
    batch_size: int = typer.Option(16, help="單次送進 embedding API 的筆數"),
    limit: int | None = typer.Option(None, help="最多處理幾筆，None 代表全部"),
) -> None:
    """為 knowledge_atoms.embedding IS NULL 的列回填向量。"""
    settings = Settings.from_env()
    embedder = EmbeddingClient(settings)

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, embedding_text
                FROM bazi.knowledge_atoms
                WHERE embedding IS NULL AND status = 'active'
                ORDER BY id
                LIMIT %s
                """,
                (limit if limit is not None else 1_000_000,),
            )
            rows = cur.fetchall()

        console.print(f"[bold]待回填 atoms：{len(rows)}[/bold]")
        total = 0
        for start in range(0, len(rows), batch_size):
            chunk = rows[start : start + batch_size]
            vectors = embedder.embed_many(text for _, text in chunk)
            with conn.cursor() as cur:
                for (atom_id, _), vec in zip(chunk, vectors, strict=True):
                    cur.execute(
                        "UPDATE bazi.knowledge_atoms SET embedding = %s WHERE id = %s",
                        (vec, atom_id),
                    )
            conn.commit()
            total += len(chunk)
            console.print(f"  已處理 {total}/{len(rows)}")

        console.print("[green]完成[/green]")


@app.command("query")
def query_cmd(
    text: str = typer.Option(..., help="Retrieval query seed 文字，用於 embedding"),
    day_master: list[str] = typer.Option([], help="日主標籤，可重複"),
    month_branch: list[str] = typer.Option([], help="月支標籤"),
    pattern: list[str] = typer.Option([], help="格局標籤"),
    seasonal: list[str] = typer.Option([], help="季節標籤"),
    top_k: int = typer.Option(10),
) -> None:
    """執行一次 filter → vector → rerank 檢索。"""
    settings = Settings.from_env()
    embedder = EmbeddingClient(settings)

    q = RetrievalQuery(
        query_text=text,
        day_master_tags=day_master,
        month_branch_tags=month_branch,
        pattern_tags=pattern,
        seasonal_tags=seasonal,
        top_k=top_k,
    )

    with connect(settings) as conn:
        hits = retrieve(conn, embedder, q)

    table = Table(title=f"Top-{top_k} retrieval results")
    table.add_column("rank", justify="right")
    table.add_column("atom_code")
    table.add_column("source")
    table.add_column("title")
    table.add_column("final", justify="right")
    table.add_column("vec", justify="right")
    table.add_column("src", justify="right")
    table.add_column("sym", justify="right")
    table.add_column("meta", justify="right")

    for i, h in enumerate(hits, 1):
        table.add_row(
            str(i),
            h.atom_code,
            h.source_book,
            (h.title or "")[:20],
            f"{h.final_score:.3f}",
            f"{h.vector_score:.3f}",
            f"{h.source_priority_score:.2f}",
            f"{h.symbolic_match_score:.2f}",
            f"{h.metadata_overlap_score:.2f}",
        )
    console.print(table)


@app.command("chart")
def chart_cmd(
    birth: str = typer.Option(..., help="ISO datetime，例如 1990-08-15T14:30:00"),
    tz: str = typer.Option("Asia/Taipei", help="IANA timezone"),
    lon: float | None = typer.Option(None, help="經度，搭配 --true-solar 使用"),
    true_solar: bool = typer.Option(False, help="套用真太陽時"),
) -> None:
    """僅排盤，不做 RAG。"""
    chart = compute_chart(birth, tz, longitude=lon, use_true_solar_time=true_solar)
    console.print_json(chart.model_dump_json(indent=2))


@app.command("analyze")
def analyze_cmd(
    birth: str = typer.Option(..., help="ISO datetime"),
    tz: str = typer.Option("Asia/Taipei"),
    lon: float | None = typer.Option(None),
    true_solar: bool = typer.Option(False),
    top_k: int = typer.Option(8),
) -> None:
    """完整流程：排盤 → 規則 → 檢索。尚不含 LLM 生成層。"""
    settings = Settings.from_env()
    embedder = EmbeddingClient(settings)

    chart = compute_chart(birth, tz, longitude=lon, use_true_solar_time=true_solar)
    rules = run_rules(chart)

    pillars = chart.four_pillars
    console.rule("[bold]命盤")
    console.print(
        f"年 {pillars['year'].stem}{pillars['year'].branch}  "
        f"月 {pillars['month'].stem}{pillars['month'].branch}  "
        f"日 [bold]{pillars['day'].stem}{pillars['day'].branch}[/bold]  "
        f"時 {pillars['hour'].stem}{pillars['hour'].branch}"
    )
    console.print(
        f"日主 {chart.day_master} | 月令 {chart.month_commander} | 季節 {chart.season}"
    )

    console.rule("[bold]規則判定")
    console.print(f"身強弱: {rules.strength_assessment.day_master_strength} "
                  f"(conf={rules.strength_assessment.confidence})")
    console.print(f"候選格局: {[p.pattern for p in rules.candidate_patterns]}")
    console.print(f"調候需求: {rules.seasonal_adjustment_needed}")
    console.print(f"風險旗標: {rules.risk_flags}")
    console.print(f"檢索種子: {rules.retrieval_query_seeds}")

    if not rules.retrieval_query_seeds:
        console.print("[yellow]無檢索種子，跳過 RAG[/yellow]")
        return

    with connect(settings) as conn:
        hits = _retrieve_for_chart(conn, embedder, chart, rules, top_k)

    console.rule("[bold]檢索結果（multi-seed max-fusion）")
    table = Table()
    table.add_column("#", justify="right")
    table.add_column("atom_code")
    table.add_column("source")
    table.add_column("original_text")
    table.add_column("final", justify="right")
    table.add_column("seeds", justify="right")
    table.add_column("top_seed")
    for i, h in enumerate(hits, 1):
        table.add_row(
            str(i), h.atom_code, h.source_book,
            (h.original_text[:38] + "…") if len(h.original_text) > 40 else h.original_text,
            f"{h.final_score:.3f}",
            str(h.hit_seed_count),
            (h.top_seed or "")[:24],
        )
    console.print(table)


@app.command("explain")
def explain_cmd(
    birth: str = typer.Option(..., help="ISO datetime"),
    tz: str = typer.Option("Asia/Taipei"),
    lon: float | None = typer.Option(None),
    true_solar: bool = typer.Option(False),
    top_k: int = typer.Option(8),
    judge: bool = typer.Option(False, help="生成後呼叫 LLM-as-judge 評估 Layer D"),
) -> None:
    """完整 end-to-end：排盤 → 規則 → 檢索 → LLM grounded 生成。"""
    settings = Settings.from_env()
    embedder = EmbeddingClient(settings)

    chart = compute_chart(birth, tz, longitude=lon, use_true_solar_time=true_solar)
    rules = run_rules(chart)

    with connect(settings) as conn:
        hits = _retrieve_for_chart(conn, embedder, chart, rules, top_k)

    console.rule("[bold]LLM 生成結果")
    result = generate_analysis(settings, chart, rules, hits)
    console.print(result.output_text)
    console.rule("[dim]usage")
    console.print(
        f"[dim]model={result.model}  "
        f"input={result.input_tokens}  output={result.output_tokens}  "
        f"cache_write={result.cache_creation_tokens}  "
        f"cache_read={result.cache_read_tokens}[/dim]"
    )

    if judge:
        console.rule("[bold]Layer D 審查（LLM-as-judge）")
        score = judge_output(settings, result.output_text, hits)
        status = "[green]PASS[/green]" if score.passed else "[red]FAIL[/red]"
        console.print(
            f"{status}  grounded={score.groundedness}  "
            f"fidelity={score.citation_fidelity}  "
            f"format={score.format_completeness}  "
            f"honesty={score.uncertainty_honesty}  "
            f"mean={score.mean:.1f}"
        )
        for issue in score.issues:
            console.print(f"  - {issue}")


@app.command("eval")
def eval_cmd(top_k: int = typer.Option(8)) -> None:
    """跑 bazi.evaluation_cases 的全部 active 案例，輸出 Phase 0 指標。"""
    settings = Settings.from_env()
    embedder = EmbeddingClient(settings)

    with connect(settings) as conn:
        summary = run_evaluation(settings, conn, embedder, top_k=top_k)

    table = Table(title="Evaluation results")
    table.add_column("case")
    table.add_column("chart")
    table.add_column("pattern")
    table.add_column("atom_recall", justify="right")
    table.add_column("notes")
    for r in summary.results:
        chart_cell = "✓" if r.passed_chart else (
            "✗ " + ",".join(k for k, v in r.chart_match.items() if not v)
        )
        pattern_cell = "-" if r.pattern_hit is None else ("✓" if r.pattern_hit else "✗")
        recall_cell = "-" if r.atom_recall is None else f"{r.atom_recall:.2f}"
        table.add_row(r.case_code, chart_cell, pattern_cell, recall_cell, r.notes)
    console.print(table)
    console.print(
        f"[bold]total={summary.total}  "
        f"chart_pass={summary.chart_pass}  "
        f"pattern_pass={summary.pattern_pass}  "
        f"atom_recall_mean={summary.atom_recall_mean:.3f}[/bold]"
    )


@app.command("ingest")
def ingest_cmd(
    path: Path = typer.Argument(..., exists=True, readable=True, help="jsonl 檔案路徑"),
) -> None:
    """讀 jsonl 原文片段，呼叫 LLM 標註為 atom 後以 status='draft' 寫入。

    寫入後需人工覆核升級為 active，再跑 destiny backfill-embeddings。
    jsonl 欄位：source_book / chapter / section / source_priority / original_text
    """
    settings = Settings.from_env()
    with connect(settings) as conn:
        ok, fail_count, failures = ingest_file(settings, conn, path)

    console.print(f"[green]ok={ok}[/green]  [red]fail={fail_count}[/red]")
    for code, issues in failures:
        console.print(f"  [red]{code}[/red]")
        for iss in issues:
            console.print(f"    - {iss.field}: {iss.message}")


if __name__ == "__main__":
    app()
