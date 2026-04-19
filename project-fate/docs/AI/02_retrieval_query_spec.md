# JR Pass RAG 系統：檢索與查詢規格

## 概述
本規格定義使用者問問題時，系統如何從向量資料庫檢索相關知識並生成回答的流程。包括輸入輸出格式、檢索策略、grounding gate、回答生成規則，以及效能與業務約束。

## 檢索流程
1. **輸入解析**：將使用者問題與行程資料標準化為查詢結構
2. **向量檢索**：根據問題 embedding 從向量資料庫檢索 Top-K 相關 chunks
3. **Metadata 過濾**：依據行程偏好（如 national/regional）過濾檢索結果
4. **Reranking**：重新排序檢索結果，優先選擇較新且相關的規則
5. **Grounding Gate**：檢查檢索結果是否足夠支撐回答
6. **回答生成**：基於通過 gate 的 chunks 生成合規性諮詢結果
7. **引用附加**：為回答附加 citations 與 grounding 狀態

## 檢索策略
- **主要策略**：Vector Retrieval + Metadata Filtering
- **進階策略**：Hybrid Search（semantic + keyword）
- **Parent-Document Retrieval**：若規則需要上下文，可回拉原始文件
- **Top-K 限制**：檢索 chunks 上限 10 個
- **Citations 限制**：最終引用上限 5 個

## Grounding Gate 規則
- **Pass**：檢索結果包含足夠官方規則依據，可生成回答
- **Fallback**：檢索結果不足，但可提供保守建議
- **Block**：檢索結果無法支撐回答，必須拒答並顯示資料不足

## 效能要求
- **p95 延遲**：< 2500ms（快取命中情況）
- **快取重用**：相同 trip_plan + 問題，30 分鐘內重用檢索結果
- **錯誤率**：grounding gate block 率 < 20%（正常查詢）
- 端點：`POST /api/jr-pass-compliance-rag/query`
- 輸入：
  - `question: string`，使用者問題，例如「東京進大阪出，7 天跑東京、京都、金澤，是否符合全國版 JR Pass 使用條件？」
  - `trip_plan: object`
  - `trip_plan.start_date: string`，出發日期，格式 `YYYY-MM-DD`
  - `trip_plan.duration_days: integer`，旅遊總天數
  - `trip_plan.arrival_city: string`，入境城市，例如 `Tokyo`、`Osaka`
  - `trip_plan.departure_city: string`，離境城市
  - `trip_plan.destinations: array<object>`，預計造訪城市與移動順序
  - `trip_plan.destinations[].city: string`，城市名稱
  - `trip_plan.destinations[].stay_days: integer`，停留天數
  - `trip_plan.transport_preferences: array<string>`，交通偏好，例如 `shinkansen`、`limited_express`、`local_train`
  - `trip_plan.pass_scope_preference: "national" | "regional" | "no_preference"`，票券範圍偏好
  - `locale: string`，回應語系，預設 `zh-TW`
- 輸出：
  - `answer: string`，最終諮詢結果
  - `summary: string`，一句話摘要
  - `recommended_passes: array<object>`，建議票券清單
  - `recommended_passes[].pass_name: string`，票券名稱
  - `recommended_passes[].pass_type: "national" | "regional"`，票券類型
  - `recommended_passes[].coverage_area: string`，適用區域
  - `recommended_passes[].valid_days: integer`，可使用天數
  - `recommended_passes[].reason: string`，建議原因
  - `recommended_passes[].limitations: array<string>`，官方限制與使用條件
  - `compliance_assessment: object`，合規判斷結果
  - `compliance_assessment.eligible: boolean`，是否符合票券適用條件
  - `compliance_assessment.rule_summary: string`，適用規則摘要
  - `comparison: object`，費用估算比較
  - `comparison.with_pass: number`，使用票券估算總成本
  - `comparison.without_pass: number`，不使用票券估算總成本
  - `comparison.savings: number`，預估節省金額
  - `citations: array<object>`，引用來源清單
  - `citations[].doc_id: string`，知識文件識別碼
  - `citations[].title: string`，文件標題
  - `citations[].excerpt: string`，實際引用片段
  - `citations[].relevance_score: number`，檢索相關度分數
  - `grounding: object`
  - `grounding.gate_status: "pass" | "fallback" | "block"`，RAG gate 結果
  - `grounding.warnings: array<string>`，知識不足、規則衝突或推論限制提示
  - `request_id: string`，請求追蹤 ID
- 錯誤處理：
  - `400 BAD_REQUEST`：缺少必要欄位、日期格式錯誤、行程欄位不完整、問題字數超限
  - `422 INVALID_ITINERARY`：行程矛盾，例如停留天數總和大於旅遊總天數
  - `422 UNSUPPORTED_QUERY`：問題超出目前支援範圍，例如非 JR Pass、非鐵道周遊券或非規則諮詢問題
  - `429 RATE_LIMITED`：使用者在短時間內超出查詢配額
  - `503 KNOWLEDGE_UNAVAILABLE`：向量檢索、引用文件或 LLM 服務暫時不可用
  - `503 INSUFFICIENT_GROUNDED_CONTEXT`：檢索結果不足以支撐回答，系統應拒答或回傳保守提示

### 約束
- 技術約束
  - 回答必須經過 retrieval gate，僅能使用通過 gate 的片段作為主要依據。
  - 行程資料需先轉成標準化 `trip_plan` 結構後才能送入查詢管線，避免 prompt 直接吃原始自由格式文字。
  - 知識文件必須保留票券名稱、區域、有效天數、適用資格、限制條件、價格版本等 metadata。
  - 向量知識庫的 chunking 策略必須保持語意完整：優先以段落為分隔，若段落過長則再依句子或片語遞迴分割，目標 chunk 大小約 600 tokens、重疊 100 tokens。
  - `citations` 至少 1 筆、至多 5 筆；若 gate 狀態為 `block`，不得偽造引用來源。
- 業務規則
  - 系統僅提供 JR Pass 與日本區域鐵道周遊券的官方規則與合規性諮詢，不得把估算結果表述為官方保證或售票承諾。
  - 若知識庫不足以支撐使用者問題，系統必須明示「資料不足」而非編造答案。
  - 回答需區分「官方規則依據」與「系統估算建議」，避免把模型自由推論包裝成官方票券條文。
  - 若使用者行程不符合任何受支援票券條件，系統必須明確說明不符合的原因，而不是強行推薦。
- 效能需求
  - 一般查詢在快取檢索完成的情況下，API `p95` 應低於 `2500ms`。
  - 單次查詢檢索 chunk 數量上限為 `10`，最終引用數上限為 `5`。
  - 相同 `trip_plan` 與問題在 30 分鐘內應可重用檢索或估算快取，降低重複計算成本。

### 參考
- 相似功能：[knowledge_query.feature](c:\Users\12ok4\project\data-science-2026\project-fate\features\knowledge_query.feature)
- 相似功能：[query_pipeline.py](c:\Users\12ok4\project\data-science-2026\project-fate\src\query\query_pipeline.py)
- 相似功能：[core.py](c:\Users\12ok4\project\data-science-2026\project-fate\src\rag\core.py)
- 文件：[ADR-001-embedding-model.md](c:\Users\12ok4\project\data-science-2026\project-fate\docs\ADR\ADR-001-embedding-model.md)
- 文件：[ADR-002-chunking-strategy.md](c:\Users\12ok4\project\data-science-2026\project-fate\docs\ADR\ADR-002-chunking-strategy.md)

### 驗收條件
- [ ] 使用者提供完整旅遊行程與問題時，系統可回傳含引用來源的 JR Pass 或區域周遊券合規性諮詢結果。
- [ ] 檢索內容不足時，系統回傳保守拒答或資料不足提示，且不產生虛構引用。
- [ ] 回應內容可區分官方規則依據、合規判斷、票券建議、費用比較與限制提醒。
- [ ] 非法日期、缺少目的地、行程矛盾等輸入會回傳明確錯誤代碼與訊息。
- [ ] 相同行程重複查詢時，可重用檢索快取並維持可接受延遲。
