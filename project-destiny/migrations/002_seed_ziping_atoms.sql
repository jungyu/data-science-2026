-- =============================================================
-- migrations/002_seed_ziping_atoms.sql
-- 子平真詮首批知識原子 seed (15 筆)
-- 說明：本檔為 Phase 0 PoC seed，embedding 欄位暫留 NULL，
--       需另由 ETL pipeline 呼叫 embedding API 回填。
-- =============================================================

BEGIN;

INSERT INTO bazi.knowledge_atoms
  (atom_code, source_book, source_priority, chapter, section, title,
   original_text, modern_interpretation, embedding_text,
   normalized_tags, logic_type, conditions,
   day_master_tags, month_branch_tags, ten_god_tags, pattern_tags, seasonal_tags,
   citation_path)
VALUES

-- ============ 十干性質 (日主天性) ============
(
  'ziping-tiangan-jia-001',
  '子平真詮', 1, '論十干', '甲木性質', '甲木棟樑參天',
  '甲木參天，脫胎要火。春不容金，秋不容土。火熾乘龍，水宕騎虎。地潤天和，植立千古。',
  '甲木為陽木，性如棟樑參天大樹；春天忌金剋，秋天忌土重，火旺時需水潤，水多時喜戊土制。',
  '甲木 陽木 棟樑 參天 脫胎要火 春不容金 秋不容土 日主性質',
  '["甲木","陽木","日主性質","調候","十干"]'::JSONB,
  '["day_master_nature"]'::JSONB,
  '[{"field":"day_master","operator":"eq","value":"甲"}]'::JSONB,
  ARRAY['甲'], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論十干","line_range":"1-6"}'::JSONB
),
(
  'ziping-tiangan-yi-001',
  '子平真詮', 1, '論十干', '乙木性質', '乙木花草柔韌',
  '乙木雖柔，刲羊解牛。懷丁抱丙，跨鳳乘猴。虛濕之地，騎馬亦憂。藤蘿繫甲，可春可秋。',
  '乙木為陰木，性如花草藤蘿；雖柔但可剋制土，若得丙丁火相隨則不畏金，若藤繞甲木則四季皆安。',
  '乙木 陰木 花草 藤蘿 柔韌 丙丁 日主性質',
  '["乙木","陰木","日主性質","藤蘿繫甲","十干"]'::JSONB,
  '["day_master_nature"]'::JSONB,
  '[{"field":"day_master","operator":"eq","value":"乙"}]'::JSONB,
  ARRAY['乙'], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論十干","line_range":"7-12"}'::JSONB
),
(
  'ziping-tiangan-bing-001',
  '子平真詮', 1, '論十干', '丙火性質', '丙火太陽猛烈',
  '丙火猛烈，欺霜侮雪。能煅庚金，逢辛反怯。土眾成慈，水猖顯節。虎馬犬鄉，甲來焚滅。',
  '丙火為陽火，性如太陽威猛；可熔庚金，遇辛金則化水反怯；土多則光輝內斂，水多時更顯節氣。',
  '丙火 陽火 太陽 猛烈 煅庚 日主性質',
  '["丙火","陽火","日主性質","太陽","十干"]'::JSONB,
  '["day_master_nature"]'::JSONB,
  '[{"field":"day_master","operator":"eq","value":"丙"}]'::JSONB,
  ARRAY['丙'], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論十干","line_range":"13-18"}'::JSONB
),

-- ============ 格局定義 (正官/七殺/財/印/食傷) ============
(
  'ziping-pattern-zhengguan-001',
  '子平真詮', 1, '論正官', '正官格成立', '正官格核心定義',
  '官以剋身，雖與七殺有別，終是剋我者，烏可忽乎？所以有貴人之稱也。',
  '正官雖剋制日主，但為陰陽相剋之正剋，不同於七殺之偏剋；能規範日主而不傷身，故主貴氣。',
  '正官格 成立 剋身 陰陽相剋 貴人 格局定義',
  '["正官格","格局定義","貴氣","剋身"]'::JSONB,
  '["pattern_definition"]'::JSONB,
  '[{"field":"month_hidden_ten_god","operator":"contains","value":"正官"}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['正官'], ARRAY['正官格'], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論正官","line_range":"1-4"}'::JSONB
),
(
  'ziping-pattern-zhengguan-002',
  '子平真詮', 1, '論正官', '正官格破格', '正官見傷官為破',
  '正官獨用，則又忌見傷官。傷官見官，為禍百端。',
  '正官格若單用正官無印化，最忌見傷官剋制正官，此為「傷官見官」，主災禍百出。',
  '正官格 破格 傷官見官 為禍百端',
  '["正官格","破格","傷官見官","風險"]'::JSONB,
  '["pattern_definition","conflict_relation"]'::JSONB,
  '[{"field":"pattern","operator":"eq","value":"正官格"},{"field":"visible_ten_gods","operator":"contains","value":"傷官"},{"field":"visible_ten_gods","operator":"not_contains","value":"正印"}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['正官','傷官'], ARRAY['正官格'], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論正官","line_range":"25-30"}'::JSONB
),
(
  'ziping-pattern-qisha-001',
  '子平真詮', 1, '論七殺', '七殺格成立', '七殺需制化',
  '煞以攻身，似非美物，而大貴之格，多存七煞。蓋有偏官而有制，則煞為我用。',
  '七殺剋身本非吉物，但大貴命格多見七殺，關鍵在於必須有食神制殺或印綬化殺，則殺為我所用。',
  '七殺格 偏官 制化 食神制殺 印化殺 大貴',
  '["七殺格","格局定義","制化","食神制殺","印化殺"]'::JSONB,
  '["pattern_definition"]'::JSONB,
  '[{"field":"month_hidden_ten_god","operator":"contains","value":"七殺"}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['七殺','食神','正印'], ARRAY['七殺格'], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論七殺","line_range":"1-6"}'::JSONB
),
(
  'ziping-pattern-zhengcai-001',
  '子平真詮', 1, '論正財', '正財格成立', '正財需日主有根',
  '財為我剋，乃我享用之物也。正財則生殺攻身，必須身強，乃可任財官。',
  '正財為日主所剋，是享用之物；但正財會生官殺剋身，故取正財格必須日主有根身強，才能任財又任官。',
  '正財格 我剋 身強 任財官 格局定義',
  '["正財格","格局定義","身強","任財官"]'::JSONB,
  '["pattern_definition","strength_assessment"]'::JSONB,
  '[{"field":"month_hidden_ten_god","operator":"contains","value":"正財"},{"field":"day_master_strength","operator":"in","value":["strong","moderately_strong"]}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['正財'], ARRAY['正財格'], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論正財","line_range":"1-5"}'::JSONB
),
(
  'ziping-pattern-zhengyin-001',
  '子平真詮', 1, '論正印', '正印格成立', '正印生身為貴',
  '印綬者，生我之神。正印為貴氣之物，能護官生身，使官不剋我。',
  '正印是生扶日主之神，能護衛正官使其不直接剋身，並將官的能量轉化為日主所用，主貴氣。',
  '正印格 生身 護官 官印相生 格局定義',
  '["正印格","格局定義","生身","官印相生"]'::JSONB,
  '["pattern_definition","ten_god_relation"]'::JSONB,
  '[{"field":"month_hidden_ten_god","operator":"contains","value":"正印"}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['正印','正官'], ARRAY['正印格'], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論正印","line_range":"1-5"}'::JSONB
),
(
  'ziping-pattern-shishen-001',
  '子平真詮', 1, '論食神', '食神格成立', '食神生財秀氣流行',
  '食神本屬洩氣，以其能生正財，所以喜之。食神生財，秀氣流行，主聰明俊秀。',
  '食神本是洩日主元氣之神，但能生正財，故為喜用；食神生財格局主人聰明俊秀，秀氣外現。',
  '食神格 洩氣 食神生財 秀氣流行 聰明',
  '["食神格","格局定義","食神生財","秀氣"]'::JSONB,
  '["pattern_definition","ten_god_relation"]'::JSONB,
  '[{"field":"month_hidden_ten_god","operator":"contains","value":"食神"}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['食神','正財'], ARRAY['食神格'], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論食神","line_range":"1-6"}'::JSONB
),
(
  'ziping-pattern-shangguan-001',
  '子平真詮', 1, '論傷官', '傷官格成立', '傷官佩印最貴',
  '傷官雖非吉神，實為秀氣。傷官佩印，貴不可言；傷官生財，富而且貴。',
  '傷官本非吉神但屬秀氣之物；若配正印則印制傷官，為「傷官佩印」主大貴；若生財則為「傷官生財」主富貴雙全。',
  '傷官格 秀氣 傷官佩印 傷官生財 富貴',
  '["傷官格","格局定義","傷官佩印","傷官生財"]'::JSONB,
  '["pattern_definition","ten_god_relation"]'::JSONB,
  '[{"field":"month_hidden_ten_god","operator":"contains","value":"傷官"}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['傷官','正印','正財'], ARRAY['傷官格'], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論傷官","line_range":"1-8"}'::JSONB
),

-- ============ 身強身弱與用神 ============
(
  'ziping-strength-shenqiang-001',
  '子平真詮', 1, '論用神', '身強取用', '身強宜洩剋耗',
  '身強者，宜洩宜剋，財官食傷皆宜。忌再見印比扶身。',
  '日主過強，宜以食傷洩秀、財星耗身、官殺剋制為用神；忌再見印綬與比劫，否則愈扶愈旺反成無用。',
  '身強 用神 洩剋耗 食傷 財官 忌印比',
  '["身強","用神","洩剋耗","食傷","財星","官殺"]'::JSONB,
  '["strength_assessment","general_principle"]'::JSONB,
  '[{"field":"day_master_strength","operator":"in","value":["strong","very_strong"]}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論用神","line_range":"22-28"}'::JSONB
),
(
  'ziping-strength-shenruo-001',
  '子平真詮', 1, '論用神', '身弱取用', '身弱宜扶',
  '身弱者，喜印比扶身，忌見財官食傷耗洩。若身弱逢官殺攻身，必藉印化。',
  '日主衰弱，喜正偏印生身、比劫助身；忌見財官食傷再洩耗日主；若身弱又見官殺剋身，必須靠印綬化官殺生身。',
  '身弱 用神 印比扶身 忌財官食傷 印化官殺',
  '["身弱","用神","印比","忌財官食傷","印化"]'::JSONB,
  '["strength_assessment","general_principle"]'::JSONB,
  '[{"field":"day_master_strength","operator":"in","value":["weak","very_weak"]}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論用神","line_range":"29-35"}'::JSONB
),

-- ============ 調候 ============
(
  'ziping-seasonal-jia-winter-001',
  '子平真詮', 1, '論甲木', '甲木冬生', '寒木需火暖局',
  '甲木參天，脫胎要火。冬生甲木，非火不溫。',
  '甲木為參天大樹，生於嚴冬水旺之時，必須見丙丁火調候暖局，否則寒木難以生發。',
  '甲木 冬生 調候 火 暖局 寒木',
  '["甲木","調候","火","冬季","寒木"]'::JSONB,
  '["seasonal_adjustment"]'::JSONB,
  '[{"field":"day_master","operator":"eq","value":"甲"},{"field":"season","operator":"in","value":["winter","late_autumn"]}]'::JSONB,
  ARRAY['甲'], ARRAY['子','亥'], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['winter','late_autumn'],
  '{"book":"子平真詮","chapter":"論甲木","line_range":"12-18"}'::JSONB
),
(
  'ziping-seasonal-bing-winter-001',
  '子平真詮', 1, '論丙火', '丙火冬生', '冬日丙火需甲木扶',
  '丙火冬生，日近黃昏，非甲引丁不暖。',
  '丙火生於冬季，火氣衰微如日近黃昏，需以甲木引丁火相助，方能保持光熱。',
  '丙火 冬生 調候 甲木 引丁 光熱衰微',
  '["丙火","調候","甲木","丁火","冬季"]'::JSONB,
  '["seasonal_adjustment"]'::JSONB,
  '[{"field":"day_master","operator":"eq","value":"丙"},{"field":"season","operator":"in","value":["winter"]}]'::JSONB,
  ARRAY['丙'], ARRAY['子','亥','丑'], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['winter'],
  '{"book":"子平真詮","chapter":"論丙火","line_range":"20-24"}'::JSONB
),

-- ============ 刑沖合害 ============
(
  'ziping-conflict-zi-wu-chong-001',
  '子平真詮', 1, '論沖合', '子午沖', '子午相沖水火激盪',
  '子午相沖，水火激戰。若居年月，主少年勞碌；居日時，主中晚年動盪。',
  '子水與午火相沖為水火激戰之局；若發生於年月柱主少年勞碌奔波，居日時柱則主中晚年動盪不安。',
  '子午沖 水火激戰 年月勞碌 日時動盪 沖合',
  '["子午沖","沖","水火激戰","動盪"]'::JSONB,
  '["conflict_relation"]'::JSONB,
  '[{"field":"branches","operator":"contains_all","value":["子","午"]}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY['子','午'], ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論沖合","line_range":"8-14"}'::JSONB
),
(
  'ziping-conflict-shangguan-jianguan-001',
  '子平真詮', 1, '論傷官', '傷官見官為禍', '傷官見官禁忌',
  '傷官見官，為禍百端。唯有傷官佩印，或傷盡官星不見，方為貴格。',
  '傷官剋制正官為命理大忌；解法有二：一為傷官佩印化傷，二為傷官極旺而完全剋盡官星不再出現。',
  '傷官見官 為禍 傷官佩印 傷盡 禁忌',
  '["傷官見官","禁忌","破格","傷官佩印"]'::JSONB,
  '["conflict_relation","pattern_definition"]'::JSONB,
  '[{"field":"visible_ten_gods","operator":"contains_all","value":["傷官","正官"]},{"field":"visible_ten_gods","operator":"not_contains","value":"正印"}]'::JSONB,
  ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY['傷官','正官','正印'], ARRAY[]::TEXT[], ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論傷官","line_range":"30-38"}'::JSONB
)

ON CONFLICT (atom_code) DO NOTHING;


-- =============================================================
-- 擴充 rule_definitions：覆蓋更多骨架規則
-- =============================================================

INSERT INTO bazi.rule_definitions
  (rule_code, version, rule_type, description, input_requirements, conditions, outputs, priority)
VALUES
(
  'PATTERN_QISHAGE_WITH_CONTROL',
  1, 'pattern',
  '七殺格成立：月令七殺透干，且見食神制殺或印化殺',
  '{"required_fields":["day_master","month_commander","visible_ten_gods"]}'::JSONB,
  '[{"field":"month_hidden_ten_god","operator":"contains","value":"七殺"},{"field":"visible_ten_gods","operator":"contains_any","value":["食神","正印","偏印"]}]'::JSONB,
  '{"candidate_pattern":"七殺格","confidence":"high","note":"有制化之七殺為用"}'::JSONB,
  20
),
(
  'RISK_SHANGGUAN_JIAN_GUAN',
  1, 'conflict',
  '傷官見官風險：命中同時出現傷官與正官且無正印',
  '{"required_fields":["visible_ten_gods"]}'::JSONB,
  '[{"field":"visible_ten_gods","operator":"contains_all","value":["傷官","正官"]},{"field":"visible_ten_gods","operator":"not_contains","value":"正印"}]'::JSONB,
  '{"risk_flag":"傷官見官","severity":"high","mitigation":"尋印化傷或去官"}'::JSONB,
  5
),
(
  'SEASONAL_ADJ_BING_WINTER',
  1, 'seasonal_adjustment',
  '丙火冬生調候：需甲木引丁或見丙火助勢',
  '{"required_fields":["day_master","season"]}'::JSONB,
  '[{"field":"day_master","operator":"eq","value":"丙"},{"field":"season","operator":"in","value":["winter"]}]'::JSONB,
  '{"adjustment_needed":["甲","丁"],"reason":"冬火衰微需木火相助"}'::JSONB,
  30
),
(
  'STRENGTH_USAGE_WEAK_DEFENSE',
  1, 'strength',
  '身弱取用：宜以印比扶身，忌再見財官食傷',
  '{"required_fields":["day_master_strength"]}'::JSONB,
  '[{"field":"day_master_strength","operator":"in","value":["weak","very_weak"]}]'::JSONB,
  '{"favored_ten_gods":["正印","偏印","比肩","劫財"],"avoided_ten_gods":["正財","偏財","正官","七殺","食神","傷官"]}'::JSONB,
  15
)
ON CONFLICT (rule_code, version) DO NOTHING;


-- =============================================================
-- knowledge_relations：建立幾筆典型關係供圖譜查詢驗證
-- =============================================================

INSERT INTO bazi.knowledge_relations (from_atom_id, relation_type, to_atom_id, weight)
SELECT f.id, 'contradicts', t.id, 1.0
FROM bazi.knowledge_atoms f, bazi.knowledge_atoms t
WHERE f.atom_code = 'ziping-pattern-zhengguan-001'
  AND t.atom_code = 'ziping-conflict-shangguan-jianguan-001'
ON CONFLICT DO NOTHING;

INSERT INTO bazi.knowledge_relations (from_atom_id, relation_type, to_atom_id, weight)
SELECT f.id, 'extends', t.id, 1.0
FROM bazi.knowledge_atoms f, bazi.knowledge_atoms t
WHERE f.atom_code = 'ziping-pattern-shangguan-001'
  AND t.atom_code = 'ziping-conflict-shangguan-jianguan-001'
ON CONFLICT DO NOTHING;

INSERT INTO bazi.knowledge_relations (from_atom_id, relation_type, to_atom_id, weight)
SELECT f.id, 'applies_to', t.id, 1.0
FROM bazi.knowledge_atoms f, bazi.knowledge_atoms t
WHERE f.atom_code = 'ziping-seasonal-jia-winter-001'
  AND t.atom_code = 'ziping-tiangan-jia-001'
ON CONFLICT DO NOTHING;


COMMIT;
