# Spec-009: 評估框架

- Status: Draft
- Owner: QA Engineer / NLP Engineer
- Last Updated: 2026-04-14

## 1. 目的

建立可回歸、可比較、可分層定位問題來源的評估系統。

## 2. 評估層次

### Layer A: 排盤正確性
| 指標 | 說明 |
|------|------|
| 四柱正確率 | 年月日時四柱全部正確 |
| 藏干正確率 | 各地支藏干正確 |
| 十神正確率 | 十神對應正確 |

### Layer B: 規則正確性
| 指標 | 說明 |
|------|------|
| 格局候選命中率 | 主要格局是否在候選清單中 |
| 強弱判定準確率 | 身強/身弱初判是否合理 |
| 調候需求準確率 | 調候方向是否正確 |

### Layer C: 檢索品質
| 指標 | 說明 |
|------|------|
| Top-K 命中率 | 核心文獻是否在 top-k 內 |
| 骨架文獻覆蓋率 | 《子平真詮》相關 atom 命中比例 |
| 多路召回貢獻率 | 各路由的有效召回比例 |

### Layer D: 生成品質
| 指標 | 說明 |
|------|------|
| Grounded 比例 | 有來源依據的結論比例 |
| 幻覺率 | 無依據或錯誤引用比例 |
| 引用正確率 | 引用與 atom 原文吻合率 |
| 格式穩定性 | 輸出區段完整率 |

## 3. 黃金資料集

每筆評估 case 包含：

```json
{
  "case_code": "eval_001",
  "input_payload": {
    "birth_datetime": "1990-08-15T14:30:00",
    "timezone": "Asia/Taipei",
    "gender": "male"
  },
  "expected_chart": {
    "day_master": "甲",
    "month_commander": "申"
  },
  "expected_features": {
    "candidate_patterns": ["正官格"],
    "strength": "moderately_strong"
  },
  "expected_atom_codes": [
    "ziping-jia-001",
    "ziping-zhengguange-001"
  ],
  "expected_source_books": ["子平真詮"],
  "notes": "申月甲木正官格標準案例"
}
```

## 4. 評估方式

| 層次 | 評估方式 |
|------|---------|
| 排盤與規則 | 單元測試 + 自動化比對 |
| 檢索管線 | 集成測試 + recall@k 計算 |
| 端到端 | 完整流程 + 人工審查抽樣 |

## 5. 最低檢查項

- 有無無來源結論（grounded check）
- 是否引用錯書（source attribution check）
- 是否將補充語料誤當核心規則（source priority check）
- 是否把不確定內容寫死（uncertainty expression check）
- 「不確定處」章節是否存在（format completeness check）

## 6. 評估週期

- 每次 schema 變更後執行完整評估
- 每次新增大批 atom 後執行 Layer C 評估
- 每次 prompt 調整後執行 Layer D 評估

## 7. 依賴 ADR

- ADR-008：評估機制與 grounded generation
