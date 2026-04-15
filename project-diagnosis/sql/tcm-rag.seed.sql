-- =========================================================
-- TCM Diagnostic RAG System — Seed Data
-- version: v0.1
-- 目的：提供 MVP 可執行的最小知識庫骨架
-- =========================================================

begin;

-- ---------------------------------------------------------
-- A. Source documents
-- ---------------------------------------------------------

insert into public.source_documents
  (id, source_type, title, canonical_title, authority_level, citation_tier,
   source_url, language_code, metadata)
values
  (
    'src_tcm_yibian_zhuangzheng',
    'html_page',
    '中醫症狀鑒別診斷學',
    '中醫症狀鑒別診斷學',
    85,
    'secondary',
    'https://yibian.hopto.org/shu/?cat=dir&sno=6',
    'zh-Hant',
    '{"publisher": "醫砭", "notes": "結構化百科，L1 資料源"}'::jsonb
  ),
  (
    'src_tcm_zhenduanxue',
    'markdown_doc',
    '中醫診斷學',
    '中醫診斷學',
    95,
    'primary',
    null,
    'zh-Hant',
    '{"publisher": "人民衛生出版社", "notes": "權威教材，L0 資料源"}'::jsonb
  ),
  (
    'src_tcm_jichulilun',
    'markdown_doc',
    '中醫基礎理論',
    '中醫基礎理論',
    95,
    'primary',
    null,
    'zh-Hant',
    '{"publisher": "人民衛生出版社", "notes": "權威教材，L0 資料源"}'::jsonb
  )
on conflict (id) do nothing;

-- ---------------------------------------------------------
-- B. Pattern atoms（證型）
-- ---------------------------------------------------------

insert into public.knowledge_atoms
  (id, source_document_id, atom_type, title, canonical_name, aliases,
   domain, category, subcategory,
   body_markdown, summary_text, embedding_text,
   quality_score, completeness_score, authority_level,
   metadata)
values
  (
    'atm_pattern_yin_deficiency_heat',
    'src_tcm_zhenduanxue',
    'pattern',
    '陰虛內熱證',
    '陰虛內熱',
    '["陰虛火旺證", "虛熱證"]'::jsonb,
    '辨證',
    '證型',
    '陰虛',
    E'[Domain=辨證][Category=證型][Pattern=陰虛內熱]\n\n陰液不足，虛熱內擾。\n\n**主要表現**：午後潮熱、夜間盜汗、口乾咽燥、五心煩熱、舌紅少苔、脈細數。\n\n**病機**：陰液虧虛，不能制陽，虛熱由內而生。\n\n**治法**：養陰清熱。',
    '以陰液不足、虛熱內擾為核心，見潮熱、盜汗、舌紅少苔、脈細數。',
    '證型 陰虛內熱 潮熱 盜汗 口乾 舌紅少苔 脈細數 養陰清熱 陰液不足',
    95,
    88,
    94,
    '{"pattern_family": "陰虛", "organ_bias": ["肝", "腎", "心"], "treatment_hint": ["養陰清熱"], "related_patterns": ["肝腎陰虛", "心腎不交"]}'::jsonb
  ),
  (
    'atm_pattern_liver_kidney_yin_def',
    'src_tcm_zhenduanxue',
    'pattern',
    '肝腎陰虛證',
    '肝腎陰虛',
    '["肝腎不足"]'::jsonb,
    '辨證',
    '證型',
    '陰虛',
    E'[Domain=辨證][Category=證型][Pattern=肝腎陰虛]\n\n肝腎陰液虧損，虛熱內擾。\n\n**主要表現**：腰膝酸軟、頭暈耳鳴、潮熱盜汗、口乾、舌紅少苔、脈細數。\n\n**病機**：肝腎陰液虧損，失於滋養，虛熱內生。\n\n**治法**：滋補肝腎，養陰清熱。',
    '肝腎陰液虧損，見腰膝酸軟、頭暈耳鳴、潮熱盜汗、脈細數。',
    '證型 肝腎陰虛 腰膝酸軟 頭暈 耳鳴 盜汗 舌紅少苔 脈細數 滋補肝腎',
    92,
    85,
    93,
    '{"pattern_family": "陰虛", "organ_bias": ["肝", "腎"], "treatment_hint": ["滋補肝腎", "養陰清熱"], "related_patterns": ["陰虛內熱", "心腎不交"]}'::jsonb
  ),
  (
    'atm_pattern_wei_qi_insecurity',
    'src_tcm_zhenduanxue',
    'pattern',
    '衛氣不固證',
    '衛氣不固',
    '["表虛自汗", "肺衛不固"]'::jsonb,
    '辨證',
    '證型',
    '氣虛',
    E'[Domain=辨證][Category=證型][Pattern=衛氣不固]\n\n衛氣虛弱，腠理不固。\n\n**主要表現**：自汗，惡風，容易感冒，神疲乏力，舌淡，脈虛弱或浮而無力。\n\n**病機**：衛氣虛弱，不能固護體表，腠理開洩。\n\n**治法**：益氣固表，調和營衛。',
    '衛氣虛弱，腠理不固，見自汗、惡風、神疲，舌淡脈虛。',
    '證型 衛氣不固 自汗 惡風 畏風 神疲 舌淡 脈虛 益氣固表',
    93,
    87,
    94,
    '{"pattern_family": "氣虛", "organ_bias": ["肺", "脾"], "treatment_hint": ["益氣固表"], "related_patterns": ["肺氣虛", "脾肺氣虛"], "formula_hint": ["玉屏風散"]}'::jsonb
  ),
  (
    'atm_pattern_lung_qi_def',
    'src_tcm_zhenduanxue',
    'pattern',
    '肺氣虛證',
    '肺氣虛',
    '["肺氣不足"]'::jsonb,
    '辨證',
    '證型',
    '氣虛',
    E'[Domain=辨證][Category=證型][Pattern=肺氣虛]\n\n肺氣虛衰，宣降失常。\n\n**主要表現**：咳嗽無力，聲低氣短，自汗，畏風，神疲懶言，舌淡苔白，脈虛弱。\n\n**病機**：肺氣虛弱，主氣功能減退，衛外無力。\n\n**治法**：補益肺氣，固表止汗。',
    '肺氣虛衰，見咳嗽無力、聲低氣短、自汗、畏風、脈虛弱。',
    '證型 肺氣虛 咳嗽 聲低 氣短 自汗 畏風 神疲 舌淡 脈虛 補益肺氣',
    91,
    84,
    93,
    '{"pattern_family": "氣虛", "organ_bias": ["肺"], "treatment_hint": ["補益肺氣", "固表止汗"], "related_patterns": ["衛氣不固", "脾肺氣虛"]}'::jsonb
  ),
  (
    'atm_pattern_heart_kidney_disconnect',
    'src_tcm_zhenduanxue',
    'pattern',
    '心腎不交證',
    '心腎不交',
    '["水火不濟"]'::jsonb,
    '辨證',
    '證型',
    '陰虛',
    E'[Domain=辨證][Category=證型][Pattern=心腎不交]\n\n心火偏亢，腎水不足，水火不濟。\n\n**主要表現**：心煩失眠，心悸健忘，潮熱盜汗，腰膝酸軟，舌紅，脈細數。\n\n**病機**：腎陰不足，不能上濟心火，心火偏亢，擾動心神。\n\n**治法**：滋腎陰，清心火，交通心腎。',
    '腎水不足，心火偏亢，見心煩失眠、盜汗、腰膝酸軟、舌紅脈細數。',
    '證型 心腎不交 心煩 失眠 心悸 盜汗 潮熱 腰膝酸軟 舌紅 脈細數 滋腎清心',
    90,
    83,
    92,
    '{"pattern_family": "陰虛", "organ_bias": ["心", "腎"], "treatment_hint": ["滋腎陰", "清心火"], "related_patterns": ["陰虛內熱", "肝腎陰虛"]}'::jsonb
  )
on conflict (id) do nothing;

-- ---------------------------------------------------------
-- C. Symptom atoms（症狀）
-- ---------------------------------------------------------

insert into public.knowledge_atoms
  (id, source_document_id, atom_type, title, canonical_name, aliases,
   domain, category, subcategory,
   body_markdown, summary_text, embedding_text,
   quality_score, completeness_score, authority_level,
   metadata)
values
  (
    'atm_symptom_dao_han',
    'src_tcm_yibian_zhuangzheng',
    'symptom',
    '盜汗',
    '盜汗',
    '["睡汗", "寢汗"]'::jsonb,
    '內科症狀',
    '汗證',
    '虛汗',
    E'[Domain=內科症狀][Category=汗證][Symptom=盜汗]\n\n**概念**：睡中出汗，醒後汗止，如盜賊之竊取，故名盜汗。\n\n**常見證候**：\n- 陰虛內熱：盜汗伴午後潮熱、口乾、舌紅少苔、脈細數。\n- 肝腎陰虛：盜汗伴腰膝酸軟、頭暈耳鳴。\n- 心腎不交：盜汗伴心煩失眠、心悸。\n\n**鑑別重點**：\n- 盜汗（陰虛）vs 自汗（氣虛）：盜汗多睡中，自汗多日間活動後或靜時。\n- 若盜汗伴畏寒肢冷，應考慮陽虛浮越，不可一概視為陰虛。',
    '睡中出汗，醒後汗止。多屬陰虛，常見於陰虛內熱、肝腎陰虛、心腎不交。',
    '症狀 盜汗 睡中汗出 醒後汗止 陰虛內熱 肝腎陰虛 心腎不交',
    90,
    85,
    85,
    '{"symptom_family": "汗證", "related_patterns": ["陰虛內熱", "肝腎陰虛", "心腎不交"], "time_bias": ["夜間", "睡中"]}'::jsonb
  ),
  (
    'atm_symptom_zi_han',
    'src_tcm_yibian_zhuangzheng',
    'symptom',
    '自汗',
    '自汗',
    '["漏汗", "不因勞而汗"]'::jsonb,
    '內科症狀',
    '汗證',
    '虛汗',
    E'[Domain=內科症狀][Category=汗證][Symptom=自汗]\n\n**概念**：不因勞動、飲食、衣被過暖或藥物等因素，而白晝時時汗出，動則尤甚。\n\n**常見證候**：\n- 衛氣不固：自汗伴惡風、容易感冒、舌淡、脈虛。\n- 肺氣虛：自汗伴聲低氣短、咳嗽無力。\n- 脾肺氣虛：自汗伴食少便溏、腹脹。\n\n**鑑別重點**：\n- 自汗（氣虛）vs 盜汗（陰虛）：自汗多日間，盜汗多夜間。\n- 若自汗伴五心煩熱，則需考慮氣陰兩虛。',
    '日間不因勞動而汗出，動則尤甚。多屬氣虛，見於衛氣不固、肺氣虛。',
    '症狀 自汗 日間出汗 動則汗出 衛氣不固 肺氣虛 氣虛',
    89,
    84,
    85,
    '{"symptom_family": "汗證", "related_patterns": ["衛氣不固", "肺氣虛", "脾肺氣虛"], "time_bias": ["日間"]}'::jsonb
  ),
  (
    'atm_symptom_chao_re',
    'src_tcm_yibian_zhuangzheng',
    'symptom',
    '潮熱',
    '潮熱',
    '["午後潮熱", "骨蒸潮熱"]'::jsonb,
    '內科症狀',
    '發熱',
    '虛熱',
    E'[Domain=內科症狀][Category=發熱][Symptom=潮熱]\n\n**概念**：發熱如潮水有規律，定時出現或定時加重，多見於午後。\n\n**常見證候**：\n- 陰虛潮熱：午後潮熱伴盜汗、舌紅少苔、脈細數。\n- 陽明腑實：午後潮熱伴腹脹、便秘、脈沉實有力。\n- 濕溫：午後潮熱伴頭身困重、苔膩。\n\n**鑑別重點**：\n- 陰虛潮熱：低熱，手足心熱，舌紅少苔。\n- 陽明實熱：高熱，腹脹，大便乾結，苔黃厚。',
    '定時發熱，如潮水起伏，多見午後。陰虛者伴盜汗舌紅，陽明者伴腹脹便結。',
    '症狀 潮熱 午後潮熱 定時發熱 陰虛 陽明腑實 骨蒸',
    88,
    82,
    85,
    '{"symptom_family": "發熱", "related_patterns": ["陰虛內熱", "肝腎陰虛"], "time_bias": ["午後"]}'::jsonb
  ),
  (
    'atm_symptom_bi_han',
    'src_tcm_yibian_zhuangzheng',
    'symptom',
    '畏風',
    '畏風',
    '["惡風", "怕風"]'::jsonb,
    '內科症狀',
    '惡寒',
    '表虛',
    E'[Domain=內科症狀][Category=惡寒][Symptom=畏風]\n\n**概念**：遇風則惡，加衣保暖後可緩解，為表虛不固之象。\n\n**常見證候**：\n- 衛氣不固：畏風伴自汗、易感冒、舌淡、脈浮弱。\n- 風寒表虛：畏風伴發熱、惡寒、脈浮緩（桂枝湯證）。\n\n**鑑別重點**：\n- 畏風（惡風）：風來則惡，非風寒感冒時即存在，多為體質性表虛。\n- 惡寒：無論有無風，均感寒冷，為風寒表證之主症。',
    '遇風則惡，多屬表虛不固，見於衛氣不固、風寒表虛。',
    '症狀 畏風 惡風 表虛 衛氣不固 自汗 易感冒',
    87,
    80,
    84,
    '{"symptom_family": "惡寒", "related_patterns": ["衛氣不固", "肺氣虛"]}'::jsonb
  ),
  (
    'atm_symptom_xin_fan',
    'src_tcm_yibian_zhuangzheng',
    'symptom',
    '心煩',
    '心煩',
    '["煩躁", "虛煩"]'::jsonb,
    '內科症狀',
    '神志',
    '心神不寧',
    E'[Domain=內科症狀][Category=神志][Symptom=心煩]\n\n**概念**：心中煩悶不安，難以自持。\n\n**常見證候**：\n- 陰虛火旺：心煩伴失眠、潮熱盜汗、舌紅少苔、脈細數。\n- 心腎不交：心煩伴失眠、腰膝酸軟、遺精。\n- 熱擾心神：心煩伴高熱、面赤、舌紅苔黃、脈數有力。\n\n**鑑別重點**：\n- 虛煩（陰虛）：低熱，手足心熱，舌紅少苔。\n- 實煩（熱盛）：高熱，面赤，苔黃厚，脈洪數。',
    '心中煩悶不安。虛煩見於陰虛火旺、心腎不交；實煩見於熱擾心神。',
    '症狀 心煩 煩躁 虛煩 陰虛火旺 心腎不交 失眠',
    88,
    82,
    84,
    '{"symptom_family": "神志", "related_patterns": ["陰虛內熱", "心腎不交"]}'::jsonb
  )
on conflict (id) do nothing;

-- ---------------------------------------------------------
-- D. Tongue feature atoms（舌象）
-- ---------------------------------------------------------

insert into public.knowledge_atoms
  (id, source_document_id, atom_type, title, canonical_name, aliases,
   domain, category,
   body_markdown, summary_text, embedding_text,
   quality_score, completeness_score, authority_level,
   metadata)
values
  (
    'atm_tongue_red_scanty_coat',
    'src_tcm_zhenduanxue',
    'tongue_feature',
    '舌紅少苔',
    '舌紅少苔',
    '["舌紅苔少", "舌紅無苔"]'::jsonb,
    '診法',
    '舌診',
    E'[Domain=診法][Category=舌診][Feature=舌紅少苔]\n\n**意義**：陰液虧虛，虛熱內生。\n\n- 舌質紅：主熱，陰虛生熱或實熱均可見，但少苔提示非實熱。\n- 少苔 / 無苔：胃陰虧虛，化生不足，苔失榮養。\n\n**臨床意義**：\n陰虛內熱、肝腎陰虛、心腎不交等陰虛類證型的強支持訊號。\n\n**鑑別**：\n- 舌紅苔黃膩：濕熱，不屬陰虛。\n- 舌絳無苔：陰虧較重，多見溫病後期。',
    '陰液虧虛的重要舌診指標，陰虛類證型的強支持訊號。',
    '舌象 舌紅少苔 陰虛 虛熱 胃陰虧虛 陰虛內熱',
    95,
    90,
    95,
    '{"diagnostic_weight": 0.90, "pattern_family": "陰虛", "related_patterns": ["陰虛內熱", "肝腎陰虛", "心腎不交"]}'::jsonb
  ),
  (
    'atm_tongue_pale',
    'src_tcm_zhenduanxue',
    'tongue_feature',
    '舌淡',
    '舌淡',
    '["舌色淡白", "舌質淡"]'::jsonb,
    '診法',
    '舌診',
    E'[Domain=診法][Category=舌診][Feature=舌淡]\n\n**意義**：氣血不足或陽氣虛弱。\n\n- 舌淡白：氣血兩虛或寒凝。\n- 舌淡胖：陽虛、水濕內停。\n\n**臨床意義**：\n氣虛、血虛、陽虛類證型的支持訊號。\n\n**鑑別**：\n- 舌淡 vs 舌紅：前者氣血虧，後者熱或陰虛。',
    '氣血不足或陽虛，氣虛類證型的支持訊號。',
    '舌象 舌淡 氣虛 血虛 陽虛 氣血不足',
    92,
    88,
    93,
    '{"diagnostic_weight": 0.75, "pattern_family": "氣虛", "related_patterns": ["衛氣不固", "肺氣虛"]}'::jsonb
  )
on conflict (id) do nothing;

-- ---------------------------------------------------------
-- E. Pulse feature atoms（脈象）
-- ---------------------------------------------------------

insert into public.knowledge_atoms
  (id, source_document_id, atom_type, title, canonical_name, aliases,
   domain, category,
   body_markdown, summary_text, embedding_text,
   quality_score, completeness_score, authority_level,
   metadata)
values
  (
    'atm_pulse_xi_shu',
    'src_tcm_zhenduanxue',
    'pulse_feature',
    '脈細數',
    '脈細數',
    '["細數脈"]'::jsonb,
    '診法',
    '脈診',
    E'[Domain=診法][Category=脈診][Feature=脈細數]\n\n**意義**：陰虛內熱的典型脈象。\n\n- 細脈：脈形細如線，主血虛、陰虛。\n- 數脈：一息五至以上，主熱。\n- 細數合見：陰虛火旺，虛熱內擾。\n\n**臨床意義**：陰虛類證型的強支持脈象。',
    '陰虛內熱的典型脈象，細主陰虛，數主熱，合見屬虛熱。',
    '脈象 細數脈 陰虛內熱 虛熱 血虛 陰虛火旺',
    93,
    88,
    93,
    '{"diagnostic_weight": 0.85, "pattern_family": "陰虛", "related_patterns": ["陰虛內熱", "肝腎陰虛", "心腎不交"]}'::jsonb
  ),
  (
    'atm_pulse_xu',
    'src_tcm_zhenduanxue',
    'pulse_feature',
    '脈虛',
    '脈虛',
    '["虛脈", "脈虛弱"]'::jsonb,
    '診法',
    '脈診',
    E'[Domain=診法][Category=脈診][Feature=脈虛]\n\n**意義**：氣血不足，正氣虛衰。\n\n- 虛脈：舉按無力，脈形鬆軟。主氣虛、血虛。\n- 臨床意義：氣虛類證型的支持脈象。',
    '氣血不足，正氣虛衰，氣虛類證型的支持脈象。',
    '脈象 虛脈 脈虛弱 氣虛 血虛 正氣不足',
    90,
    85,
    92,
    '{"diagnostic_weight": 0.75, "pattern_family": "氣虛", "related_patterns": ["衛氣不固", "肺氣虛"]}'::jsonb
  )
on conflict (id) do nothing;

-- ---------------------------------------------------------
-- F. Atom relations
-- ---------------------------------------------------------

insert into public.atom_relations
  (id, from_atom_id, relation_type, to_atom_id, weight, evidence_note)
values
  -- 盜汗 → 各陰虛類證型
  ('rel_dao_han_suggests_yin_heat',       'atm_symptom_dao_han',        'suggests',           'atm_pattern_yin_deficiency_heat',       0.60, '盜汗是陰虛內熱的常見主症'),
  ('rel_dao_han_suggests_lky_def',        'atm_symptom_dao_han',        'suggests',           'atm_pattern_liver_kidney_yin_def',      0.55, '肝腎陰虛常見夜間盜汗'),
  ('rel_dao_han_suggests_hk_disconnect',  'atm_symptom_dao_han',        'suggests',           'atm_pattern_heart_kidney_disconnect',   0.50, '心腎不交常伴盜汗'),

  -- 自汗 → 氣虛類證型
  ('rel_zi_han_suggests_wei_qi',          'atm_symptom_zi_han',         'suggests',           'atm_pattern_wei_qi_insecurity',         0.65, '自汗為衛氣不固的主症之一'),
  ('rel_zi_han_suggests_lung_qi',         'atm_symptom_zi_han',         'suggests',           'atm_pattern_lung_qi_def',               0.55, '肺氣虛衛外無力，可見自汗'),

  -- 潮熱 → 陰虛類證型
  ('rel_chao_re_strengthens_yin_heat',    'atm_symptom_chao_re',        'strengthens',        'atm_pattern_yin_deficiency_heat',       0.70, '午後潮熱是陰虛內熱的特徵性症狀'),
  ('rel_chao_re_strengthens_lky_def',     'atm_symptom_chao_re',        'strengthens',        'atm_pattern_liver_kidney_yin_def',      0.60, '肝腎陰虛常伴潮熱'),

  -- 畏風 → 氣虛類證型
  ('rel_bi_han_suggests_wei_qi',          'atm_symptom_bi_han',         'suggests',           'atm_pattern_wei_qi_insecurity',         0.65, '畏風為衛氣不固的特徵性症狀'),
  ('rel_bi_han_suggests_lung_qi',         'atm_symptom_bi_han',         'suggests',           'atm_pattern_lung_qi_def',               0.55, '肺氣虛衛外無力，常見畏風'),

  -- 心煩 → 陰虛類證型
  ('rel_xin_fan_strengthens_yin_heat',    'atm_symptom_xin_fan',        'strengthens',        'atm_pattern_yin_deficiency_heat',       0.60, '陰虛內熱可見心煩'),
  ('rel_xin_fan_strengthens_hk_disc',     'atm_symptom_xin_fan',        'strongly_strengthens','atm_pattern_heart_kidney_disconnect',  0.80, '心煩失眠是心腎不交的核心症狀'),

  -- 舌紅少苔 → 陰虛類證型（強訊號）
  ('rel_tongue_red_ss_yin_heat',          'atm_tongue_red_scanty_coat', 'strongly_strengthens','atm_pattern_yin_deficiency_heat',       0.90, '舌紅少苔是陰虛內熱的強烈支持訊號'),
  ('rel_tongue_red_ss_lky_def',           'atm_tongue_red_scanty_coat', 'strongly_strengthens','atm_pattern_liver_kidney_yin_def',      0.85, '舌紅少苔支持肝腎陰虛'),
  ('rel_tongue_red_ss_hk_disc',           'atm_tongue_red_scanty_coat', 'strengthens',        'atm_pattern_heart_kidney_disconnect',   0.80, '舌紅少苔支持心腎不交'),

  -- 舌淡 → 氣虛類證型
  ('rel_tongue_pale_s_wei_qi',            'atm_tongue_pale',            'strengthens',        'atm_pattern_wei_qi_insecurity',         0.70, '舌淡支持衛氣不固（氣虛）'),
  ('rel_tongue_pale_s_lung_qi',           'atm_tongue_pale',            'strengthens',        'atm_pattern_lung_qi_def',               0.70, '舌淡支持肺氣虛'),

  -- 脈細數 → 陰虛類證型（強訊號）
  ('rel_pulse_xs_ss_yin_heat',            'atm_pulse_xi_shu',           'strongly_strengthens','atm_pattern_yin_deficiency_heat',       0.88, '脈細數是陰虛內熱的典型脈象'),
  ('rel_pulse_xs_ss_lky_def',             'atm_pulse_xi_shu',           'strongly_strengthens','atm_pattern_liver_kidney_yin_def',      0.85, '脈細數支持肝腎陰虛'),
  ('rel_pulse_xs_ss_hk_disc',             'atm_pulse_xi_shu',           'strengthens',        'atm_pattern_heart_kidney_disconnect',   0.80, '脈細數支持心腎不交'),

  -- 脈虛 → 氣虛類證型
  ('rel_pulse_xu_s_wei_qi',               'atm_pulse_xu',               'strengthens',        'atm_pattern_wei_qi_insecurity',         0.75, '脈虛支持衛氣不固'),
  ('rel_pulse_xu_s_lung_qi',              'atm_pulse_xu',               'strengthens',        'atm_pattern_lung_qi_def',               0.75, '脈虛支持肺氣虛'),

  -- 衝突關係：陰虛與氣虛的主症互斥
  ('rel_bi_han_conflicts_yin_heat',       'atm_symptom_bi_han',         'conflicts_with',     'atm_pattern_yin_deficiency_heat',       0.60, '畏風為氣虛、表虛之象，與陰虛內熱傾向有衝突'),
  ('rel_zi_han_conflicts_yin_heat',       'atm_symptom_zi_han',         'conflicts_with',     'atm_pattern_yin_deficiency_heat',       0.50, '純自汗傾向氣虛，若無盜汗、潮熱，不強支持陰虛'),
  ('rel_tongue_pale_conflicts_yin_heat',  'atm_tongue_pale',            'conflicts_with',     'atm_pattern_yin_deficiency_heat',       0.70, '舌淡屬氣虛，與陰虛內熱（舌紅）方向相反'),
  ('rel_dao_han_conflicts_wei_qi',        'atm_symptom_dao_han',        'conflicts_with',     'atm_pattern_wei_qi_insecurity',         0.55, '盜汗傾向陰虛，與氣虛自汗傾向有別')

on conflict (from_atom_id, relation_type, to_atom_id) do nothing;

-- ---------------------------------------------------------
-- G. Diagnostic rules
-- ---------------------------------------------------------

insert into public.diagnostic_rules
  (id, rule_code, rule_name, rule_scope, status, priority,
   target_atom_id, conditions, actions, explanation)
values
  (
    'rule_yin_heat_core_trio',
    'TCM-RULE-001',
    '陰虛內熱核心三症',
    'pattern_ranking',
    'active',
    10,
    'atm_pattern_yin_deficiency_heat',
    '{
      "all_of": [
        {"type": "symptom", "value": "盜汗"}
      ],
      "any_of": [
        {"type": "symptom", "value": "潮熱"},
        {"type": "tongue_feature", "value": "舌紅少苔"}
      ],
      "none_of": [],
      "score_delta": 0.40
    }'::jsonb,
    '{
      "action": "boost_pattern",
      "pattern_id": "atm_pattern_yin_deficiency_heat",
      "boost": 0.40
    }'::jsonb,
    '盜汗 + 潮熱或舌紅少苔，高度支持陰虛內熱。'
  ),
  (
    'rule_wei_qi_core_trio',
    'TCM-RULE-002',
    '衛氣不固核心三症',
    'pattern_ranking',
    'active',
    10,
    'atm_pattern_wei_qi_insecurity',
    '{
      "all_of": [
        {"type": "symptom", "value": "自汗"},
        {"type": "symptom", "value": "畏風"}
      ],
      "any_of": [
        {"type": "tongue_feature", "value": "舌淡"},
        {"type": "pulse_feature", "value": "脈虛"}
      ],
      "none_of": [
        {"type": "tongue_feature", "value": "舌紅少苔"}
      ],
      "score_delta": 0.40
    }'::jsonb,
    '{
      "action": "boost_pattern",
      "pattern_id": "atm_pattern_wei_qi_insecurity",
      "boost": 0.40
    }'::jsonb,
    '自汗 + 畏風 + 舌淡或脈虛（無舌紅少苔），高度支持衛氣不固。'
  ),
  (
    'rule_yin_qi_conflict',
    'TCM-RULE-003',
    '陰虛氣虛主症衝突偵測',
    'differential_diagnosis',
    'active',
    20,
    null,
    '{
      "all_of": [
        {"type": "symptom", "value": "盜汗"},
        {"type": "symptom", "value": "自汗"}
      ],
      "score_delta": 0
    }'::jsonb,
    '{
      "action": "flag_ambiguous",
      "message": "同時出現盜汗與自汗，需進一步確認是否為氣陰兩虛，或詢問各症狀的明顯程度。",
      "suggest_question": "自汗與盜汗哪個較明顯？是否有五心煩熱？"
    }'::jsonb,
    '盜汗與自汗並見，可能為氣陰兩虛，需鑑別。'
  ),
  (
    'rule_missing_pulse_ask',
    'TCM-RULE-004',
    '缺脈象時建議補問',
    'question_suggestion',
    'active',
    50,
    null,
    '{
      "missing": ["pulse_feature"],
      "any_candidate_patterns": ["陰虛內熱", "肝腎陰虛", "衛氣不固"]
    }'::jsonb,
    '{
      "action": "suggest_question",
      "message": "目前缺少脈象資訊，建議補問：脈是細、數、虛、弦，還是其他？"
    }'::jsonb,
    '候選證型包含陰虛或氣虛類，脈象為重要鑑別依據，應建議補問。'
  )
on conflict (id) do nothing;

commit;
