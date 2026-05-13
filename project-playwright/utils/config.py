"""跨模組共用常數（timeouts / batch limits / lease 設定）。

集中管理 magic numbers，避免散落於各章腳本與 worker 內部。
教學腳本（ch08）與正式 worker（utils/worker）使用不同的 timeout，
是刻意保留的差異 — 教學用短逾時讓學員更快看到失敗回饋。
"""

from __future__ import annotations

# ── Playwright 導航 timeout（毫秒） ─────────────────────────────────
# 正式 worker：較寬鬆，給慢站台容忍空間
WORKER_NAV_TIMEOUT_MS = 30_000
# 教學腳本：快速失敗，便於課堂演示
TEACHING_NAV_TIMEOUT_MS = 15_000

# ── crawl_queue 設定 ──────────────────────────────────────────────
# Lease 持有時間；過期後其他 Worker 可重新搶租
LEASE_DURATION_MINUTES = 5
# 單次 list 頁面最多入隊的 article URL 數量
DISCOVERY_BATCH_LIMIT = 20

# ── RAG bridge 驗收查詢 ───────────────────────────────────────────
RAG_VERIFY_QUERY_LIMIT = 500
