"""HITLChecker 的風險等級判定與豁免機制測試。"""

from src.governance.hitl_checker import HITLChecker


class TestHITLChecker:
    def setup_method(self):
        self.checker = HITLChecker()

    # --- Level 1 測試 ---

    def test_level1_always_blocks(self):
        """Level 1 操作無論如何都要停止"""
        for op in HITLChecker.LEVEL_1_OPS:
            can_proceed, reason = self.checker.should_proceed(op, {})
            assert not can_proceed, f"{op} 應該被阻擋"
            assert "Level 1" in reason

    def test_level1_not_exempt_by_session(self):
        """Level 1 即使 session 授權也不放行"""
        ctx = {"authorized_ops": ["modify_constitution"]}
        can_proceed, _ = self.checker.should_proceed("modify_constitution", ctx)
        assert not can_proceed

    # --- Level 2 測試 ---

    def test_level2_blocks_by_default(self):
        """Level 2 預設阻擋"""
        can_proceed, reason = self.checker.should_proceed("create_namespace", {})
        assert not can_proceed
        assert "Level 2" in reason

    def test_level2_exempt_by_session_auth(self):
        """豁免 1：Session 授權"""
        ctx = {"authorized_ops": ["create_namespace"]}
        can_proceed, reason = self.checker.should_proceed("create_namespace", ctx)
        assert can_proceed
        assert "Session 已授權" in reason

    def test_level2_exempt_by_task_pack(self):
        """豁免 2：Task Pack 核准"""
        ctx = {"task_pack": {"approved_operations": ["batch_ingest_large"]}}
        can_proceed, reason = self.checker.should_proceed("batch_ingest_large", ctx)
        assert can_proceed
        assert "Task Pack" in reason

    def test_level2_exempt_by_urgent_fix(self):
        """豁免 3：緊急修復模式"""
        ctx = {"mode": "urgent_fix"}
        can_proceed, reason = self.checker.should_proceed("create_namespace", ctx)
        assert can_proceed
        assert "緊急修復" in reason

    # --- Level 3 測試 ---

    def test_level3_always_proceeds(self):
        """Level 3（未知操作）直接放行"""
        can_proceed, reason = self.checker.should_proceed("read_document", {})
        assert can_proceed
        assert "Level 3" in reason

    # --- 分類正確性 ---

    def test_risk_level_classification(self):
        """驗證操作分類正確性"""
        assert self.checker._get_risk_level("modify_constitution") == 1
        assert self.checker._get_risk_level("create_namespace") == 2
        assert self.checker._get_risk_level("unknown_op") == 3
