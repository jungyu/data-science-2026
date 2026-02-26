"""
知識漂移偵測器：定期掃描知識庫，偵測品質下滑的早期訊號。
建議每週由 cron job 或 GitHub Actions 自動執行。

來源：第五章 — Knowledge Drift Detection
"""

from datetime import datetime


class KnowledgeDriftDetector:
    """
    定期掃描知識庫，偵測品質下滑的早期訊號。
    對應：Constitution Principle I（知識品質優先）
    """

    THRESHOLDS = {
        "fresh_ratio_warning": 0.75,    # 新鮮文件比例 < 75% 發出警告
        "fresh_ratio_critical": 0.60,   # 新鮮文件比例 < 60% 觸發緊急處理
        "deprecated_ratio_max": 0.10,   # 廢棄文件比例 > 10% 需要清理
    }

    def __init__(self, vector_db: object, alert_manager: object) -> None:
        self.vector_db = vector_db
        self.alert_manager = alert_manager

    def run_weekly_scan(self) -> dict:
        """執行每週知識品質掃描"""
        # 從向量 DB 取得所有文件的 metadata 摘要
        all_docs = self.vector_db.list_documents_metadata()

        report: dict = {}
        for namespace in self._get_all_namespaces(all_docs):
            ns_docs = [d for d in all_docs if d["namespace"] == namespace]
            report[namespace] = self._analyze_namespace(ns_docs)

        # 觸發告警
        self._trigger_alerts(report)
        return report

    def _get_all_namespaces(self, docs: list[dict]) -> set[str]:
        """從文件列表中提取所有不重複的 namespace。"""
        return {d["namespace"] for d in docs if "namespace" in d}

    def _analyze_namespace(self, docs: list[dict]) -> dict:
        now = datetime.now()
        total = len(docs)
        if total == 0:
            return {"status": "empty", "total": 0}

        fresh = sum(
            1
            for d in docs
            if (now - datetime.fromisoformat(d["last_updated"])).days <= 180
        )
        deprecated = sum(1 for d in docs if d.get("status") == "deprecated")

        fresh_ratio = fresh / total
        deprecated_ratio = deprecated / total

        # 判定狀態
        if fresh_ratio < self.THRESHOLDS["fresh_ratio_critical"]:
            status = "critical"
        elif fresh_ratio < self.THRESHOLDS["fresh_ratio_warning"]:
            status = "warning"
        elif deprecated_ratio > self.THRESHOLDS["deprecated_ratio_max"]:
            status = "needs_cleanup"
        else:
            status = "healthy"

        return {
            "status": status,
            "total_docs": total,
            "fresh_docs": fresh,
            "fresh_ratio": round(fresh_ratio, 3),
            "deprecated_docs": deprecated,
            "oldest_doc": min(d["last_updated"] for d in docs),
        }

    def _trigger_alerts(self, report: dict) -> None:
        for namespace, stats in report.items():
            if stats.get("status") == "critical":
                self.alert_manager.send_urgent(
                    f"[{namespace}] 知識庫嚴重老化！"
                    f"新鮮文件比例：{stats['fresh_ratio']:.0%}，"
                    f"立即通知各文件 owner 審核更新。"
                )
            elif stats.get("status") == "warning":
                self.alert_manager.send_warning(
                    f"[{namespace}] 知識庫開始老化，"
                    f"新鮮文件比例：{stats['fresh_ratio']:.0%}"
                )
