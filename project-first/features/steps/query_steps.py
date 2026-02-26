"""
BDD step definitions for knowledge_query.feature.
Stub implementations — 完成 Ch05/Ch06 實作後接入真實模組。
"""

from behave import given, when, then


@given('向量 DB 中有 "{namespace}" 的文件')
def step_namespace_has_documents(context, namespace):
    context.namespace = namespace


@given('使用者屬於 "{department}" 部門')
def step_user_department(context, department):
    context.user_department = department


@given('使用者有 "{namespace}" 的查詢權限')
def step_user_has_permission(context, namespace):
    context.allowed_namespaces = [namespace]


@given('使用者沒有 "{namespace}" 的查詢權限')
def step_user_no_permission(context, namespace):
    context.forbidden_namespaces = [namespace]


@given('向量 DB 中沒有 "{topic}" 相關的文件')
def step_no_documents_for_topic(context, topic):
    context.no_results_topic = topic


@when('使用者問「{question}」')
def step_user_asks(context, question):
    context.question = question
    # TODO: 接入 RAGQueryPipeline
    context.answer = {"answer": "", "sources": [], "gate_status": "pass"}


@then("系統應該回傳包含答案的回應")
def step_verify_answer(context):
    pass  # TODO: 驗證答案非空


@then("回應中應該包含文件來源引用")
def step_verify_sources(context):
    pass  # TODO: 驗證 sources 非空


@then('系統應該回應「{message}」')
def step_verify_message(context, message):
    pass  # TODO: 驗證回應包含指定訊息


@then("不應該返回任何相關文件")
def step_verify_no_results(context):
    pass  # TODO: 驗證無結果


@then('不應該返回來自 "{namespace}" 的內容')
def step_verify_namespace_isolation(context, namespace):
    pass  # TODO: 驗證 namespace 隔離
