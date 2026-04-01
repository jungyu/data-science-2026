"""
Policies — 重試策略與速率限制。

- retry_policy     ：decide_retry()，核心重試決策
- rate_limit_policy：DomainLimiter + SourceHealthTracker
"""
