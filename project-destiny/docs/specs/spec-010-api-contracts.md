# Spec-010: API 契約

- Status: Draft
- Owner: Backend Engineer
- Last Updated: 2026-04-14

## 1. 目的

定義系統主要 API 的請求與回應格式。

## 2. API 清單

| Method | Path | 說明 |
|--------|------|------|
| POST | `/api/bazi/chart` | 排盤 |
| POST | `/api/bazi/analyze` | 完整解盤流程 |
| POST | `/api/knowledge/ingest` | 匯入知識 atom |
| POST | `/api/retrieval/query` | 執行檢索 |
| POST | `/api/evaluation/run` | 執行評估集 |

## 3. POST `/api/bazi/chart`

**Request**
```json
{
  "birth_datetime": "1990-08-15T14:30:00",
  "timezone": "Asia/Taipei",
  "location": { "lat": 25.0330, "lng": 121.5654 },
  "gender": "male",
  "calendar_type": "solar",
  "use_true_solar_time": true
}
```

**Response**
```json
{
  "chart_id": "chart_xxx",
  "four_pillars": { ... },
  "day_master": "甲",
  "hidden_stems": { ... },
  "ten_gods": { ... },
  "month_commander": "申",
  "season": "autumn",
  "true_solar_time_applied": true
}
```

## 4. POST `/api/bazi/analyze`

**Request**（同 chart，加上分析參數）
```json
{
  "birth_datetime": "1990-08-15T14:30:00",
  "timezone": "Asia/Taipei",
  "gender": "male",
  "use_true_solar_time": true,
  "options": {
    "top_k": 12,
    "source_scope": ["子平真詮", "滴天髓"],
    "output_format": "structured"
  }
}
```

**Response**
```json
{
  "chart": { ... },
  "rule_output": {
    "candidate_patterns": ["正官格"],
    "strength_assessment": { ... },
    "retrieval_query_seeds": [...]
  },
  "retrieval": {
    "retrieval_id": "ret_001",
    "results": [ ... ]
  },
  "analysis": {
    "命盤結構摘要": "...",
    "核心判斷": "...",
    "依據文獻": [ ... ],
    "規則說明": "...",
    "綜合解釋": "...",
    "不確定處": "..."
  }
}
```

## 5. POST `/api/knowledge/ingest`

**Request**
```json
{
  "atoms": [
    {
      "atom_code": "ziping-jia-001",
      "source_book": "子平真詮",
      "source_priority": 1,
      "original_text": "甲木參天，脫胎要火。",
      "embedding_text": "甲木 冬季 調候 火",
      "normalized_tags": ["甲木", "調候", "火"],
      "logic_type": ["day_master_nature", "seasonal_adjustment"],
      "conditions": [ ... ]
    }
  ]
}
```

**Response**
```json
{
  "ingested": 1,
  "failed": 0,
  "errors": []
}
```

## 6. API 設計原則

- `chart` 與 `analysis` 在 response 中嚴格分離
- `rule_output` 不可省略（必須出現在 analyze response）
- `retrieval` 結果應可供前端做 trace view
- 所有 POST 均返回 `request_id` 供追蹤

## 7. 依賴 ADR

- ADR-001：混合式檢索
- ADR-003：確定性排盤
- ADR-008：可追溯性
