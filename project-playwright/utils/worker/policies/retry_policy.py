"""
retry_policy — 重試決策。

實作邏輯在 utils/worker/retry.py，這裡提供對應 10_ 文件的匯入路徑。
PageRunner 從 policies.retry_policy 匯入，不直接依賴 retry 模組名稱。
"""

from utils.worker.retry import decide_retry, _calculate_backoff

__all__ = ["decide_retry", "_calculate_backoff"]
