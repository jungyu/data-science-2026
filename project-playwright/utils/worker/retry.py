"""
Retry 策略、指數退避與來源健康追蹤。

來源文件：docs/supabase/04_crawler/07_worker-retry-and-anti-ban.md

包含：
    - decide_retry()    — 核心重試決策（不可重試 / 超限 / 退避）
    - SourceHealthTracker — 來源層級健康狀態機（healthy → degraded → cooldown → blocked）
    - DomainLimiter     — 每網域並行信號量

佇列狀態機（供參考）：
    pending → leased → running → done
                              ↘ transient error → pending（重排程）
                              ↘ policy denied  → skipped
                              ↘ too many fail  → dead
                              ↘ permanent error→ failed
"""

from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timedelta, timezone

from utils.worker.types import (
    RetryContext,
    RetryDecision,
    RetryDecisionDead,
    RetryDecisionFail,
    RetryDecisionRetry,
    RetryDecisionSkip,
    SourceHealth,
    SourceHealthState,
    WorkerError,
    WorkerErrorCode,
)

# ── 錯誤分類常數 ──────────────────────────────────────────────────

# 永遠不應重試的錯誤
NOT_RETRYABLE: set[WorkerErrorCode] = {
    WorkerErrorCode.HTTP_404,
    WorkerErrorCode.ROBOTS_DENIED,
    WorkerErrorCode.UNSUPPORTED_CONTENT,
}

# 需要來源層級冷卻後才能重試的錯誤
NEEDS_COOLDOWN: set[WorkerErrorCode] = {
    WorkerErrorCode.HTTP_429,
    WorkerErrorCode.HTTP_403,
    WorkerErrorCode.CAPTCHA_DETECTED,
}


# ── 核心重試決策 ──────────────────────────────────────────────────

def decide_retry(error: WorkerError, ctx: RetryContext) -> RetryDecision:
    """根據錯誤碼、retryable 旗標與重試次數決定後續行動。

    決策順序：
      1. NOT_RETRYABLE 錯誤 → 立即失敗
      2. error.retryable=False → 失敗
      3. retry_count >= max_retries → 進死信
      4. 計算退避時間 → 重試
    """
    if error.code in NOT_RETRYABLE:
        return RetryDecisionFail(reason=f"Non-retryable: {error.code.value}")

    if not error.retryable:
        return RetryDecisionFail(reason=error.message)

    if ctx.retry_count >= ctx.max_retries:
        return RetryDecisionDead(
            reason=f"Max retries ({ctx.max_retries}) exceeded"
        )

    retry_at = _calculate_backoff(ctx.retry_count, error.code)
    return RetryDecisionRetry(
        retry_at=retry_at.isoformat(),
        reason=f"Retry #{ctx.retry_count + 1}: {error.code.value}",
    )


def _calculate_backoff(retry_count: int, error_code: WorkerErrorCode) -> datetime:
    """指數退避 + 隨機抖動。

    一般錯誤（base 60s × 2^n）：   冷卻類錯誤（×3 倍）：
      attempt 0: ~1 min               attempt 0: ~3 min
      attempt 1: ~2 min               attempt 1: ~6 min
      attempt 2: ~4 min               attempt 2: ~12 min
      attempt 3: ~8 min               attempt 3: ~24 min
      attempt 4: ~16 min              attempt 4: ~48 min

    上限：4 小時。抖動：±20%。
    """
    base_seconds = 60.0
    delay = base_seconds * math.pow(2, retry_count)

    if error_code in NEEDS_COOLDOWN:
        delay *= 3

    delay = min(delay, 4 * 3600)

    jitter = delay * 0.2 * (2 * random.random() - 1)
    delay += jitter

    return datetime.now(timezone.utc) + timedelta(seconds=delay)


# ── 來源健康追蹤器 ────────────────────────────────────────────────

class SourceHealthTracker:
    """追蹤每個來源的健康狀態並套用冷卻機制。

    狀態機：
        healthy → degraded → cooldown → blocked
                                      ↗ （冷卻期過後）
    """

    def __init__(self) -> None:
        self._health: dict[str, SourceHealth] = {}

    def get(self, source_id: str) -> SourceHealth:
        if source_id not in self._health:
            self._health[source_id] = SourceHealth(source_id=source_id)
        return self._health[source_id]

    def record_success(self, source_id: str) -> None:
        h = self.get(source_id)
        h.consecutive_failures = 0
        h.consecutive_429s = 0
        h.consecutive_403s = 0
        h.state = SourceHealthState.HEALTHY

    def record_failure(self, source_id: str, error: WorkerError) -> None:
        h = self.get(source_id)
        h.consecutive_failures += 1

        if error.code == WorkerErrorCode.HTTP_429:
            h.consecutive_429s += 1
        elif error.code == WorkerErrorCode.HTTP_403:
            h.consecutive_403s += 1

        # 從最嚴重往輕微判斷
        if h.consecutive_failures >= 10:
            h.state = SourceHealthState.BLOCKED
        elif h.consecutive_429s >= 3 or h.consecutive_403s >= 2:
            h.state = SourceHealthState.COOLDOWN
            h.penalty_until = (
                datetime.now(timezone.utc) + timedelta(minutes=15)
            ).isoformat()
        elif h.consecutive_failures >= 5:
            h.state = SourceHealthState.DEGRADED

    def is_available(self, source_id: str) -> bool:
        """回傳 False 表示來源目前應暫停爬取。"""
        h = self.get(source_id)
        if h.state == SourceHealthState.BLOCKED:
            return False
        if h.penalty_until:
            if datetime.now(timezone.utc) < datetime.fromisoformat(h.penalty_until):
                return False
            # 冷卻期已過，自動恢復
            h.state = SourceHealthState.HEALTHY
            h.penalty_until = None
        return True


# ── 網域並行限制器 ────────────────────────────────────────────────

class DomainLimiter:
    """每個網域各自持有一個 asyncio.Semaphore，限制並行請求數。

    用法（在 async consume loop 中）：
        await limiter.acquire(domain)
        try:
            result = await runner.process(job)
        finally:
            limiter.release(domain)
    """

    def __init__(self, default_max: int = 1) -> None:
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._default_max = default_max

    def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._semaphores:
            self._semaphores[domain] = asyncio.Semaphore(self._default_max)
        return self._semaphores[domain]

    async def acquire(self, domain: str) -> None:
        await self._get_semaphore(domain).acquire()

    def release(self, domain: str) -> None:
        self._get_semaphore(domain).release()


# ── 封鎖信號偵測 ──────────────────────────────────────────────────

def detect_ban_signals(signal) -> list[str]:
    """辨識來源可能正在封鎖我們的信號。

    Args:
        signal: ResponseSignal 實例

    Returns:
        警告字串清單（空表示無異常）
    """
    warnings: list[str] = []

    if signal.http_status == 429:
        warnings.append("rate_limited")
    if signal.http_status == 403:
        warnings.append("forbidden")
    if signal.has_captcha:
        warnings.append("captcha_detected")
    if signal.has_challenge:
        warnings.append("challenge_page")
    if signal.is_empty_body:
        warnings.append("suspicious_empty_body")
    if signal.is_redirect_loop:
        warnings.append("redirect_loop")
    if signal.ttfb_ms and signal.ttfb_ms > 15000:
        warnings.append("unusually_slow_ttfb")

    return warnings
