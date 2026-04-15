"""ETL pipeline — 將古籍原文片段半自動轉為 knowledge_atoms (Spec-003 / 003a)。

流程：
    raw .jsonl ─▶ annotate_with_llm ─▶ validate_against_schema ─▶ insert (status='draft')
    人工覆核 ─▶ 升級 status='active' ─▶ backfill embedding

輸入格式（jsonl，一行一段）：
    {"source_book": "子平真詮", "chapter": "論正官", "section": "正官格總論",
     "source_priority": 1, "original_text": "官以剋身...", "line_range": "1-4"}

輸出：每段產生一筆符合 schemas/knowledge-atom.schema.json 的 atom JSON。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import psycopg
from anthropic import Anthropic

from destiny.config import Settings

_CONTROLLED_VOCAB = """
【受控詞彙表（normalized_tags 可選項）】
天干：甲 乙 丙 丁 戊 己 庚 辛 壬 癸
地支：子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥
十神：比肩 劫財 食神 傷官 偏財 正財 七殺 正官 偏印 正印
格局：正官格 七殺格 正財格 偏財格 正印格 偏印格 食神格 傷官格 比劫格 建祿格 陽刃格
主題：調候 用神 身強 身弱 制化 破格 變格 秀氣 貴氣 日主性質
關係：沖 合 刑 害 破 三會 三合

【Bazi Engine 可用欄位（conditions.field 僅能從此選）】
day_master | month_commander | season | day_master_strength |
four_pillars | hidden_stems | visible_ten_gods | month_hidden_ten_god |
branches | pattern | risk_flags
"""

_SYSTEM_PROMPT = f"""你是熟稔八字子平命理與古籍訓詁的知識工程師。
將一段古籍原文轉換為符合 knowledge-atom schema 的 JSON。

嚴格規則：
1. original_text 必須完整保留原文，不得增刪字句。
2. 不得自行創造原文中不存在的論斷。
3. normalized_tags 必須從受控詞彙表選擇。
4. logic_type 必須從以下枚舉值選擇：
   day_master_nature | pattern_definition | strength_assessment |
   seasonal_adjustment | ten_god_relation | conflict_relation |
   case_example | general_principle
5. conditions.field 只能從 Bazi Engine 欄位白名單選擇，不可發明欄位。
6. 若原文過於抽象無法抽出結構化條件，conditions 留空陣列，不可硬編。
7. 若一段承載多個不相干命題，回報 split_required=true。

輸出格式：僅 JSON object，無 markdown fence、無前後說明文字。
{_CONTROLLED_VOCAB}
"""

_REQUIRED_FIELDS = {
    "atom_code", "source_book", "source_priority",
    "original_text", "embedding_text", "normalized_tags",
    "logic_type", "conditions", "status",
}

_ALLOWED_LOGIC_TYPES = {
    "day_master_nature", "pattern_definition", "strength_assessment",
    "seasonal_adjustment", "ten_god_relation", "conflict_relation",
    "case_example", "general_principle",
}


@dataclass
class ValidationIssue:
    field: str
    message: str


def validate_atom(atom: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    missing = _REQUIRED_FIELDS - set(atom)
    for f in missing:
        issues.append(ValidationIssue(f, "missing required field"))

    if (lt := atom.get("logic_type")):
        for t in lt:
            if t not in _ALLOWED_LOGIC_TYPES:
                issues.append(ValidationIssue("logic_type", f"unknown value: {t}"))

    if atom.get("original_text", "").strip() == "":
        issues.append(ValidationIssue("original_text", "must not be empty"))

    if not isinstance(atom.get("normalized_tags", []), list) or not atom.get("normalized_tags"):
        issues.append(ValidationIssue("normalized_tags", "must be non-empty array"))

    return issues


def annotate_with_llm(
    settings: Settings,
    raw: dict,
    client: Anthropic | None = None,
) -> dict:
    """呼叫 Claude 將 raw 片段轉為 atom JSON。"""
    client = client or Anthropic()
    user_content = (
        f"【來源書目】{raw['source_book']}\n"
        f"【章節】{raw.get('chapter', '')} / {raw.get('section', '')}\n"
        f"【權威層級】{raw.get('source_priority', 4)}\n"
        f"【原文片段】\n{raw['original_text']}\n"
    )
    resp = client.messages.create(
        model=settings.chat_model,
        max_tokens=1024,
        system=[{"type": "text", "text": _SYSTEM_PROMPT,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    # 去除 markdown code fence（防呆）
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return json.loads(text)


def insert_draft(conn: psycopg.Connection, atom: dict) -> int:
    """寫入 knowledge_atoms，status='draft'，embedding 留 NULL。回傳 id。"""
    sql = """
        INSERT INTO bazi.knowledge_atoms (
          atom_code, source_book, source_priority, chapter, section, title,
          original_text, modern_interpretation, embedding_text,
          normalized_tags, logic_type, conditions,
          day_master_tags, month_branch_tags, ten_god_tags, pattern_tags, seasonal_tags,
          citation_path, status
        ) VALUES (
          %(atom_code)s, %(source_book)s, %(source_priority)s, %(chapter)s, %(section)s, %(title)s,
          %(original_text)s, %(modern_interpretation)s, %(embedding_text)s,
          %(normalized_tags)s::jsonb, %(logic_type)s::jsonb, %(conditions)s::jsonb,
          %(day_master_tags)s, %(month_branch_tags)s, %(ten_god_tags)s,
          %(pattern_tags)s, %(seasonal_tags)s,
          %(citation_path)s::jsonb, 'draft'
        )
        ON CONFLICT (atom_code) DO UPDATE SET
          original_text = EXCLUDED.original_text,
          modern_interpretation = EXCLUDED.modern_interpretation,
          embedding_text = EXCLUDED.embedding_text,
          normalized_tags = EXCLUDED.normalized_tags,
          logic_type = EXCLUDED.logic_type,
          conditions = EXCLUDED.conditions,
          updated_at = NOW()
        RETURNING id
    """
    params = {
        "atom_code": atom["atom_code"],
        "source_book": atom["source_book"],
        "source_priority": atom["source_priority"],
        "chapter": atom.get("chapter"),
        "section": atom.get("section"),
        "title": atom.get("title"),
        "original_text": atom["original_text"],
        "modern_interpretation": atom.get("modern_interpretation"),
        "embedding_text": atom["embedding_text"],
        "normalized_tags": json.dumps(atom["normalized_tags"], ensure_ascii=False),
        "logic_type": json.dumps(atom["logic_type"], ensure_ascii=False),
        "conditions": json.dumps(atom.get("conditions", []), ensure_ascii=False),
        "day_master_tags": atom.get("day_master_tags", []),
        "month_branch_tags": atom.get("month_branch_tags", []),
        "ten_god_tags": atom.get("ten_god_tags", []),
        "pattern_tags": atom.get("pattern_tags", []),
        "seasonal_tags": atom.get("seasonal_tags", []),
        "citation_path": json.dumps(atom.get("citation_path", {}), ensure_ascii=False),
    }
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        assert row is not None
        return row[0]


def ingest_file(
    settings: Settings,
    conn: psycopg.Connection,
    jsonl_path: Path,
) -> tuple[int, int, list[tuple[str, list[ValidationIssue]]]]:
    """讀 jsonl → 逐行標註 → 驗證 → 寫入 draft。

    回傳: (success_count, fail_count, failures)
    """
    client = Anthropic()
    ok = 0
    fail: list[tuple[str, list[ValidationIssue]]] = []

    for i, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        try:
            atom = annotate_with_llm(settings, raw, client=client)
        except Exception as e:
            fail.append((f"line-{i}", [ValidationIssue("annotate", str(e))]))
            continue

        issues = validate_atom(atom)
        if issues:
            fail.append((atom.get("atom_code") or f"line-{i}", issues))
            continue

        insert_draft(conn, atom)
        conn.commit()
        ok += 1

    return ok, len(fail), fail
