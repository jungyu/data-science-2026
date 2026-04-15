-- =============================================================
-- migrations/003_more_evaluation_cases.sql
-- 擴充黃金評估案例至 5+ 筆（Phase 1 完成條件）
-- =============================================================

BEGIN;

INSERT INTO bazi.evaluation_cases
  (case_code, input_payload, expected_chart, expected_features,
   expected_atom_codes, expected_source_books, notes)
VALUES
(
  'eval-003-bingfo-zi',
  '{"birth_datetime":"1988-01-05T10:00:00","timezone":"Asia/Taipei","gender":"male","use_true_solar_time":false}'::JSONB,
  '{"day_master":"丙","season":"winter"}'::JSONB,
  '{"seasonal_adjustment_needed":["木","火"]}'::JSONB,
  '["ziping-seasonal-bing-winter-001"]'::JSONB,
  '["子平真詮"]'::JSONB,
  '丙火冬生需甲木引丁 — 調候案例'
),
(
  'eval-004-shangguan-jianguan',
  '{"birth_datetime":"1992-06-10T08:30:00","timezone":"Asia/Taipei","gender":"female","use_true_solar_time":false}'::JSONB,
  '{}'::JSONB,
  '{"risk_flags":["傷官見官"]}'::JSONB,
  '["ziping-pattern-zhengguan-002","ziping-conflict-shangguan-jianguan-001"]'::JSONB,
  '["子平真詮"]'::JSONB,
  '傷官見官為禍 — 風險旗標偵測案例（實際旗標需命盤實測確認）'
),
(
  'eval-005-zi-wu-chong',
  '{"birth_datetime":"1995-05-20T23:30:00","timezone":"Asia/Taipei","gender":"male","use_true_solar_time":false}'::JSONB,
  '{}'::JSONB,
  '{}'::JSONB,
  '["ziping-conflict-zi-wu-chong-001"]'::JSONB,
  '["子平真詮"]'::JSONB,
  '子午沖 — 沖合刑害偵測案例'
),
(
  'eval-006-qisha-zhi-hua',
  '{"birth_datetime":"1975-09-20T03:00:00","timezone":"Asia/Taipei","gender":"male","use_true_solar_time":false}'::JSONB,
  '{}'::JSONB,
  '{"candidate_patterns":["七殺格"]}'::JSONB,
  '["ziping-pattern-qisha-001"]'::JSONB,
  '["子平真詮"]'::JSONB,
  '七殺格制化 — 格局候選案例'
)
ON CONFLICT (case_code) DO NOTHING;

COMMIT;
