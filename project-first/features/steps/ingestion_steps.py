"""
BDD step definitions for knowledge_ingestion.feature.
Stub implementations — 完成 Ch06 實作後接入真實模組。
"""

from behave import given, when, then


@given("向量資料庫已連線")
def step_vector_db_connected(context):
    context.vector_db = {}  # stub


@given('嵌入模型為 "{model}"')
def step_embedding_model(context, model):
    context.embedding_model = model


@given('一份 approved 的文件 "{filename}"')
def step_approved_document(context, filename):
    context.document = {
        "filename": filename,
        "status": "approved",
        "last_updated": "2026-02-01",
    }


@given('namespace 為 "{namespace}"')
def step_namespace(context, namespace):
    context.namespace = namespace


@given('一份 last_updated 超過 180 天的文件 "{filename}"')
def step_expired_document(context, filename):
    context.document = {
        "filename": filename,
        "status": "approved",
        "last_updated": "2025-06-01",
    }


@given("批次攝取 10 份文件中第 7 份失敗")
def step_batch_failure(context):
    context.batch_failure_at = 7


@when("執行攝取操作")
def step_execute_ingest(context):
    # TODO: 接入 KnowledgeIngestor
    context.ingest_result = {"success": True}


@when("執行攝取操作時")
def step_execute_ingest_attempt(context):
    # TODO: 接入 KnowledgeIngestor with precondition check
    context.ingest_result = {"success": False, "error": "expired"}


@when("使用 atomic_knowledge_update 執行批次攝取")
def step_atomic_batch_ingest(context):
    # TODO: 接入 atomic_knowledge_update context manager
    context.ingest_result = {"success": False, "rolled_back": True}


@then('向量 DB 中應有 "{namespace}" 的 chunks')
def step_verify_chunks_exist(context, namespace):
    pass  # TODO: 查詢向量 DB 驗證


@then("每個 chunk 都帶有完整的 metadata")
def step_verify_metadata(context):
    pass  # TODO: 驗證 metadata 完整性


@then("Action Log 應記錄此次攝取")
def step_verify_action_log(context):
    pass  # TODO: 檢查 Action Log


@then("系統應拒絕攝取")
def step_verify_rejection(context):
    assert context.ingest_result.get("success") is False


@then('錯誤訊息應包含 "{message}"')
def step_verify_error_message(context, message):
    pass  # TODO: 驗證錯誤訊息


@then("前 6 份文件的 chunks 應該被回滾")
def step_verify_rollback(context):
    assert context.ingest_result.get("rolled_back") is True


@then("向量 DB 中不應有此批次的殘餘 chunks")
def step_verify_no_residual(context):
    pass  # TODO: 查詢向量 DB 驗證無殘餘
