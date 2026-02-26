# 檔案：features/knowledge_ingestion.feature

Feature: 知識攝取（Knowledge Ingestion）
  作為 知識庫管理員
  我想要 將企業文件安全地納入 RAG 系統
  以便 員工能夠透過 AI 查詢正確的企業知識

  Background:
    Given 系統已連接到向量資料庫
    And 嵌入模型 text-embedding-3-large 已就緒

  Scenario: 成功攝取已審核的 HR 文件
    Given 一份 PDF 文件「年假政策 2026.pdf」
    And 文件的 metadata 包含 owner="hr-team", status="approved", last_updated="2026-01-15"
    When 知識庫管理員執行 /ingest hr-policies/年假政策2026.pdf
    Then 文件應該被分割成 3-8 個 chunks
    And 每個 chunk 應該被成功嵌入並存入向量 DB
    And chunk 的 namespace 應該是 "hr-leaves"
    And 系統應該回報「攝取成功，共 N 個 chunks」

  Scenario: 拒絕攝取過期文件
    Given 一份文件「報銷規定 2023.pdf」
    And 文件的 last_updated 距今超過 180 天
    When 知識庫管理員執行 /ingest finance/報銷規定2023.pdf
    Then 系統應該拒絕攝取
    And 回報錯誤「文件已超過 180 天未更新，請聯繫 owner 審核後再攝取」
    And 向量 DB 中不應該有此文件的任何 chunk

  Scenario: 攝取失敗時不留下殘餘 chunks（原子性）
    Given 一份 50 頁的文件正在攝取
    When 攝取到第 30 頁時 OpenAI API 回傳錯誤
    Then 系統應該回滾（rollback）已攝取的 30 頁 chunks
    And 向量 DB 中不應該有此批次的任何 chunk
    And 回報錯誤日誌給管理員
