# 檔案：features/knowledge_query.feature

Feature: 知識查詢（Knowledge Query）
  作為 企業員工
  我想要 用自然語言詢問 AI 企業內部政策
  以便 快速找到正確答案而不需要手動翻閱文件

  Scenario: 成功查詢並引用正確來源
    Given 向量 DB 中有「年假政策 2026.pdf」的 chunks
    When 員工問「我每年有幾天年假？」
    Then 系統應該檢索到年假政策相關的 chunks（Hit@5）
    And 生成的答案應該基於這些 chunks
    And 答案末尾應該列出引用的文件來源
    And 答案不應該包含「根據現有文件無法回答」

  Scenario: 文件不存在時誠實回應
    Given 向量 DB 中沒有「股票期權政策」相關文件
    When 員工問「公司的股票期權怎麼計算？」
    Then 系統應該回應「根據現有文件無法回答」
    And 不應該自行推測或給出不確定的答案
    And 可以建議「請聯繫 HR 部門了解詳情」

  Scenario: 跨部門查詢被隔離拒絕
    Given 員工只有 HR 命名空間的存取權限
    When 員工問「Q4 的財務報告顯示什麼？」
    Then 系統不應該在財務命名空間中搜尋
    And 回應「您沒有權限查詢財務相關資訊」
