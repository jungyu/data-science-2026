"""
Human-in-the-Loop (HITL) 檢查器：
在執行高風險操作前，檢查是否需要人類確認。

來源：第八章 — HITL 豁免機制
"""


class HITLChecker:
    """
    在執行高風險操作前，檢查是否需要人類確認。
    有三種豁免條件。
    """

    # Level 1：必須停止等待確認的操作
    LEVEL_1_OPS = frozenset([
        "change_embedding_model",
        "change_namespace_permissions",
        "modify_constitution",
        "bulk_delete_documents",
        "production_deploy",
    ])

    # Level 2：建議確認的操作
    LEVEL_2_OPS = frozenset([
        "create_namespace",
        "batch_ingest_large",
        "change_chunking_params",
        "modify_retrieval_gate_thresholds",
        "add_new_dependency",
    ])

    def should_proceed(
        self,
        operation: str,
        session_context: dict,
    ) -> tuple[bool, str]:
        """
        回傳 (是否可以繼續, 原因說明)
        """
        level = self._get_risk_level(operation)

        if level == 1:
            # LEVEL 1：無論如何都必須停止等待確認
            return False, (
                f"操作「{operation}」屬於 Level 1 高風險操作，"
                f"必須等待管理員確認後才能繼續。"
            )

        if level == 2:
            # LEVEL 2：有三種豁免條件

            # 豁免 1：Session 授權
            if operation in session_context.get("authorized_ops", []):
                return True, "Session 已授權此操作"

            # 豁免 2：Task Pack 核准
            if self._is_approved_in_task_pack(operation, session_context):
                return True, "Task Pack 已核准此操作"

            # 豁免 3：緊急修復模式
            if session_context.get("mode") == "urgent_fix":
                return True, "緊急修復模式，Level 2 操作自動授權"

            # 沒有豁免條件：建議確認
            return False, (
                f"操作「{operation}」屬於 Level 2 中風險操作，"
                f"建議確認後繼續。"
                f"如需授權，請在 session 開始時說明。"
            )

        # LEVEL 3：直接執行，完成後通知
        return True, "Level 3 操作，執行後將通知管理員"

    def _get_risk_level(self, operation: str) -> int:
        """根據操作類型判定風險等級。"""
        if operation in self.LEVEL_1_OPS:
            return 1
        if operation in self.LEVEL_2_OPS:
            return 2
        return 3

    def _is_approved_in_task_pack(
        self, operation: str, session_context: dict
    ) -> bool:
        """檢查 Task Pack 是否已核准此操作。"""
        task_pack = session_context.get("task_pack", {})
        approved_ops = task_pack.get("approved_operations", [])
        return operation in approved_ops
