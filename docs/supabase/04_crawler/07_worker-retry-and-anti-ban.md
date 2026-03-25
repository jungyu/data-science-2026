# Playwright Worker — Retry、Backoff 與反封鎖設計

---

## 佇列任務狀態機

```text
pending
  | lease
leased
  | start
running
  |-- success --> done
  |-- transient error --> pending (rescheduled)
  |-- policy denied --> skipped
  |-- too many failures --> dead
  +-- permanent error --> failed
```

## 來源健康狀態機

```text
healthy
  | repeated timeout / 429
degraded
  | more failures
cooldown
  | long-term failures / repeated blocks
blocked
  | manual review / cooldown expires
healthy
```

---

## 錯誤分類

### 可重試

- Timeout
- DNS 暫時性失敗
- 502 / 503 / 504
- Target closed
- 導覽中斷
- 暫時性瀏覽器崩潰
- 暫時性網路重置

### 條件性可重試

- 403（可能為永久封鎖）
- 429（速率限制，需要冷卻）
- 空內容（可能是時序問題）
- Selector 缺失（網站可能已變更版面）
- 登入重導向

### 不可重試

- 404
- robots.txt 拒絕
- 無效 URL
- 不支援的內容類型
- 永久性 Schema 不符
- 手動政策拒絕

---

## Retry 策略實作

```python
import math
import random
from datetime import datetime, timedelta, timezone

from .types import (
    RetryContext,
    RetryDecision,
    RetryDecisionDead,
    RetryDecisionFail,
    RetryDecisionRetry,
    RetryDecisionSkip,
    WorkerError,
    WorkerErrorCode,
)

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


def decide_retry(error: WorkerError, ctx: RetryContext) -> RetryDecision:
    """核心重試決策邏輯。"""

    # 永久性錯誤 -> 立即失敗
    if error.code in NOT_RETRYABLE:
        return RetryDecisionFail(reason=f"Non-retryable: {error.code.value}")

    # 明確標記為不可重試
    if not error.retryable:
        return RetryDecisionFail(reason=error.message)

    # 超過最大重試次數 -> 進入死信
    if ctx.retry_count >= ctx.max_retries:
        return RetryDecisionDead(
            reason=f"Max retries ({ctx.max_retries}) exceeded"
        )

    # 計算 Backoff
    retry_at = _calculate_backoff(ctx.retry_count, error.code)

    return RetryDecisionRetry(
        retry_at=retry_at.isoformat(),
        reason=f"Retry #{ctx.retry_count + 1}: {error.code.value}",
    )


def _calculate_backoff(retry_count: int, error_code: WorkerErrorCode) -> datetime:
    """指數退避加隨機抖動。

    一般錯誤：                      冷卻類錯誤（429/403/captcha，x3）：
      attempt 0: ~1 min              attempt 0: ~3 min
      attempt 1: ~2 min              attempt 1: ~6 min
      attempt 2: ~4 min              attempt 2: ~12 min
      attempt 3: ~8 min              attempt 3: ~24 min
      attempt 4: ~16 min             attempt 4: ~48 min
    """
    base_seconds = 60
    delay = base_seconds * math.pow(2, retry_count)

    # 速率限制 / 封鎖信號需要更長的退避時間
    if error_code in NEEDS_COOLDOWN:
        delay *= 3

    # 上限為 4 小時
    delay = min(delay, 4 * 3600)

    # 加入抖動：+/- 20%
    jitter = delay * 0.2 * (2 * random.random() - 1)
    delay += jitter

    return datetime.now(timezone.utc) + timedelta(seconds=delay)
```

---

## 網域層級速率限制

### 為何以網域為單位，而非以任務為單位

如果某個來源持續回傳 429 / 403 / captcha，重試個別任務並沒有幫助。你需要的是**來源層級的節流**。

### 來源健康追蹤器

```python
from datetime import datetime, timedelta, timezone

from .types import (
    SourceHealth,
    SourceHealthState,
    WorkerError,
    WorkerErrorCode,
)


class SourceHealthTracker:
    """追蹤每個來源的健康狀態並套用冷卻機制。"""

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

        # 狀態轉換：先檢查最嚴重的情況
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
        h = self.get(source_id)
        if h.state == SourceHealthState.BLOCKED:
            return False
        if h.penalty_until:
            if datetime.now(timezone.utc) < datetime.fromisoformat(h.penalty_until):
                return False
            # 冷卻期已過，重置狀態
            h.state = SourceHealthState.HEALTHY
            h.penalty_until = None
        return True
```

### 網域並行限制器

```python
import asyncio


class DomainLimiter:
    """限制每個網域的並行請求數。"""

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
```

---

## 反封鎖策略

### 原則（以合規為基礎，而非規避）

| 原則                            | 實作方式                                                       |
| ------------------------------- | ------------------------------------------------------------- |
| 遵守網站政策                     | 檢查 robots.txt，優先使用 API（如有提供）                        |
| 低干擾爬蟲                       | 每網域並行限制，請求之間設定最小間隔                              |
| 只抓取所需資料                   | 在不需要用於擷取的情況下封鎖圖片/字型/媒體/分析腳本              |
| 來源專屬政策                     | 每個來源都有自己的 `SourceCrawlPolicy`                          |
| 偵測異常並退避                   | 遇到 429/403/captcha 時立即冷卻，不持續轟炸                     |
| 絕不繞過存取控制                 | 不解 CAPTCHA、不繞過挑戰、不進行憑證填充攻擊                     |

### 封鎖信號偵測

```python
from .types import ResponseSignal


def detect_ban_signals(signal: ResponseSignal) -> list[str]:
    """辨識來源可能正在封鎖我們的信號。"""
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
```

### 資源封鎖

```python
from playwright.async_api import Page


async def setup_route_blocking(page: Page, block_types: list[str] | None = None) -> None:
    """封鎖不必要的資源以減少對目標網站的負載。"""
    if not block_types:
        block_types = ["image", "font", "media", "stylesheet"]

    blocked = set(block_types)

    async def handle_route(route):
        if route.request.resource_type in blocked:
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", handle_route)
```

---

## 禁止事項

- 不得繞過 CAPTCHA / 挑戰頁面
- 不得進行憑證填充或 Session 劫持
- 不得透過 Proxy 輪換來規避 IP 封鎖
- 不得偽造 User-Agent 以冒充真實瀏覽器進行規避
- 不得在未經授權的情況下抓取登入保護的內容
- 所有失敗都必須記錄截圖 + HTML + 錯誤碼
