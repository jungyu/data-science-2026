# Spec-002: 八字排盤模組

- Status: Draft
- Owner: Backend Engineer
- Last Updated: 2026-04-14

## 1. 目的

定義八字排盤模組的輸入、輸出、責任邊界與測試要求。

## 2. 模組責任

Bazi Engine 負責：

- 曆法換算（公曆 / 農曆 / 節氣）
- 真太陽時計算
- 四柱推算
- 藏干展開
- 十神映射
- 月令與季節判定

Bazi Engine 不負責：

- 文獻檢索
- 格局最終解釋
- 自然語言輸出

## 3. Input Contract

```json
{
  "birth_datetime": "1990-08-15T14:30:00",
  "timezone": "Asia/Taipei",
  "location": {
    "lat": 25.0330,
    "lng": 121.5654
  },
  "gender": "male",
  "calendar_type": "solar",
  "use_true_solar_time": true
}
```

## 4. Output Contract

```json
{
  "chart_id": "chart_xxx",
  "four_pillars": {
    "year":  { "stem": "庚", "branch": "午" },
    "month": { "stem": "甲", "branch": "申" },
    "day":   { "stem": "甲", "branch": "子" },
    "hour":  { "stem": "辛", "branch": "未" }
  },
  "day_master": "甲",
  "hidden_stems": {
    "午": ["丁", "己"],
    "申": ["庚", "壬", "戊"],
    "子": ["癸"],
    "未": ["己", "丁", "乙"]
  },
  "ten_gods": {
    "庚": "七殺",
    "午": "傷官",
    "甲": "比肩",
    "申": "七殺",
    "子": "正印",
    "辛": "正官",
    "未": "傷官"
  },
  "month_commander": "申",
  "season": "autumn",
  "true_solar_time_applied": true,
  "calculation_meta": {
    "timezone": "Asia/Taipei",
    "solar_term_boundary_used": true
  }
}
```

## 5. 錯誤處理

| 錯誤類型 | 處理方式 |
|---------|---------|
| 缺少必要欄位 | 400 Bad Request + 錯誤欄位名稱 |
| 時區無效 | 400 + 可接受時區列表 |
| 地理座標超界 | 400 + 說明 |
| 日期格式錯誤 | 400 + ISO 8601 說明 |
| 曆法轉換失敗 | 500 + 計算細節 |

## 6. 測試要求

### 必測案例

- 節氣交界日（立春前後一日）
- 子初 / 子正時段（23:00 vs 00:00 柱位差異）
- 真太陽時前後跨柱案例
- 閏月相關日期
- 不同時區輸入（UTC / JST / CST）

### 驗收標準

- 對照人工樣本與可信排盤結果，主要邊界案例正確率達標
- 輸出欄位穩定，不隨 LLM 版本變動

## 7. 依賴 ADR

- ADR-003：確定性排盤模組
