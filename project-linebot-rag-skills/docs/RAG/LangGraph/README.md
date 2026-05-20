# LangGraph 學習指南（Head First 風格）

> 把 Agent 從「一次性函式呼叫」變成「有狀態、可分支、可中斷、可恢復的流程機器」。

這份指南用 O'Reilly Head First 的方式帶你理解 LangGraph：大量比喻、對話、圖解、思考題，少正經教科書語氣。讀完你會知道 **為什麼** RAG 需要進化成 Reflection Agent，而不只是「再呼叫一次模型」。

## 你會學到什麼？

- 為什麼一次性 RAG 在真實世界會崩
- StateGraph、Conditional Edges、Persistence、Agent Loop 這四件事為什麼是同一套哲學
- RAG / Self-RAG / Reflection Agent 三者差在哪
- 如何設計 State Schema 與 Reflection Prompt
- 如何用 LangGraph 寫出可治理、可恢復、可審計的 Agent
- pgvector + rule engine 怎麼搭配 LangGraph

## 章節地圖

| # | 章節 | 主題 |
|---|------|------|
| 01 | [為什麼需要 LangGraph](ch01-why-langgraph.md) | 從一次性 RAG 的痛點開始 |
| 02 | [StateGraph：流程的中樞神經](ch02-stategraph.md) | 狀態驅動的流程控制板 |
| 03 | [Conditional Edges：路口的號誌系統](ch03-conditional-edges.md) | 讓流程會分岔、會迴圈 |
| 04 | [Persistence：Agent 的存檔機制](ch04-persistence.md) | Checkpoint、Interrupt、Resume |
| 05 | [Agent Loop：思考、行動、觀察、重複](ch05-agent-loop.md) | 把反思變成系統結構 |
| 06 | [三種 RAG 對照](ch06-rag-vs-selfrag-vs-reflection.md) | RAG / Self-RAG / Reflection Agent |
| 07 | [State Schema 設計](ch07-state-schema.md) | 流程共用的工作筆記 |
| 08 | [Reflection Node 深潛](ch08-reflection-node.md) | 整個 Agent 的靈魂 |
| 09 | [實戰：完整 LangGraph 程式碼](ch09-langgraph-in-action.md) | 真的可跑的版本 |
| 10 | [Production 化與常見地雷](ch10-production.md) | pgvector、rule engine、反模式 |

## 怎麼讀？

- **第一次**：照順序讀 01 → 10。每章都很短，留時間給 brain power 思考題。
- **第二次**：跳到 08（Reflection）和 09（程式碼），動手做。
- **參考**：把 07（State Schema）和 10（Production）當 cheat sheet。

## 本指南定位

根目錄 README 已經從專案層級說明 LangGraph 的工程價值：確定性狀態圖、Time-Travel、人機協同與可觀測性。這份子指南不再重複那段論述，而是把那些能力拆成 10 章可實作的學習路徑：

- 想先知道「為什麼需要 LangGraph」：讀 [第 1 章](ch01-why-langgraph.md)
- 想理解狀態機與流程控制：讀 [第 2 章](ch02-stategraph.md) 和 [第 3 章](ch03-conditional-edges.md)
- 想掌握 checkpoint、interrupt、resume、time-travel：讀 [第 4 章](ch04-persistence.md)
- 想設計 Reflection Agent：讀 [第 5 章](ch05-agent-loop.md) 到 [第 8 章](ch08-reflection-node.md)
- 想直接看完整程式與上線注意事項：讀 [第 9 章](ch09-langgraph-in-action.md) 和 [第 10 章](ch10-production.md)

簡單說：**根 README 負責說明 LangGraph 為什麼重要；本指南負責教你怎麼把它做出來。**

## 一句話收斂

> 這套架構的本質，不是讓 AI 更聰明，而是讓 AI 的錯誤「可以被系統修正」。
