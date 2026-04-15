/**
 * Feature extraction for TCM diagnostic RAG query normalization.
 *
 * Input: natural-language symptom description from the user
 * Output: structured features for downstream hybrid retrieval
 *
 *   - symptoms        : 症狀（canonical_name 列表）
 *   - signs           : 體徵
 *   - tongue_features : 舌象
 *   - pulse_features  : 脈象
 *   - time_features   : 時序（午後、夜間、晨起...）
 *   - location_hints  : 部位
 *   - pattern_hints   : 初步候選證型
 *   - missing         : 尚未確認的關鍵訊號類別
 *
 * Two extraction strategies:
 *   1. Dictionary-based: exact/alias match against canonical names
 *      loaded from Postgres `knowledge_atoms`.
 *   2. LLM-based (optional): fallback when dictionary coverage is low.
 *
 * This module is deliberately dependency-light so it can be reused
 * from API routes, workers, or test harnesses.
 */

// ---------------------------------------------------------
// Types
// ---------------------------------------------------------

export type AtomType =
  | "symptom"
  | "sign"
  | "tongue_feature"
  | "pulse_feature"
  | "pattern"
  | "pathomechanism"
  | "treatment_principle"
  | "formula"
  | "herb";

export interface AtomDictionaryEntry {
  atom_id: string;
  atom_type: AtomType;
  canonical_name: string;
  aliases: string[];
}

export interface ExtractedFeatures {
  symptoms: FeatureHit[];
  signs: FeatureHit[];
  tongue_features: FeatureHit[];
  pulse_features: FeatureHit[];
  time_features: string[];
  location_hints: string[];
  pattern_hints: FeatureHit[];
  missing: MissingCategory[];
  raw_query: string;
}

export interface FeatureHit {
  atom_id: string;
  canonical_name: string;
  matched_surface: string;
  match_type: "canonical" | "alias";
}

export type MissingCategory =
  | "tongue_feature"
  | "pulse_feature"
  | "time_feature"
  | "duration"
  | "location";

// ---------------------------------------------------------
// Dictionary
// ---------------------------------------------------------

/**
 * Build a flat lookup map: surface form → atom entry.
 * Each canonical name and each alias becomes its own key.
 */
export function buildSurfaceIndex(
  dictionary: AtomDictionaryEntry[],
): Map<string, AtomDictionaryEntry> {
  const index = new Map<string, AtomDictionaryEntry>();
  for (const entry of dictionary) {
    index.set(entry.canonical_name, entry);
    for (const alias of entry.aliases ?? []) {
      if (!index.has(alias)) {
        index.set(alias, entry);
      }
    }
  }
  return index;
}

// ---------------------------------------------------------
// Time / location lexicons (lightweight)
// ---------------------------------------------------------

const TIME_LEXICON = [
  "午後",
  "下午",
  "午前",
  "上午",
  "清晨",
  "晨起",
  "夜間",
  "夜裡",
  "睡中",
  "入睡後",
  "醒後",
  "飯後",
  "空腹",
  "經期",
  "經前",
  "經後",
];

const LOCATION_LEXICON = [
  "頭",
  "胸",
  "脅",
  "脘",
  "腹",
  "腰",
  "膝",
  "四肢",
  "手足心",
  "咽",
  "口",
  "眼",
  "耳",
];

// ---------------------------------------------------------
// Extraction core
// ---------------------------------------------------------

export function extractFeatures(
  query: string,
  dictionary: AtomDictionaryEntry[],
): ExtractedFeatures {
  const surfaceIndex = buildSurfaceIndex(dictionary);
  const normalized = normalizeQuery(query);

  const hits = findDictionaryHits(normalized, surfaceIndex);

  const symptoms = hits.filter((h) => h.atom_type === "symptom");
  const signs = hits.filter((h) => h.atom_type === "sign");
  const tongue = hits.filter((h) => h.atom_type === "tongue_feature");
  const pulse = hits.filter((h) => h.atom_type === "pulse_feature");
  const patterns = hits.filter((h) => h.atom_type === "pattern");

  const time_features = TIME_LEXICON.filter((token) => normalized.includes(token));
  const location_hints = LOCATION_LEXICON.filter((token) => normalized.includes(token));

  const missing = detectMissingCategories({
    tongue: tongue.length,
    pulse: pulse.length,
    time: time_features.length,
  });

  return {
    symptoms: stripAtomType(symptoms),
    signs: stripAtomType(signs),
    tongue_features: stripAtomType(tongue),
    pulse_features: stripAtomType(pulse),
    time_features,
    location_hints,
    pattern_hints: stripAtomType(patterns),
    missing,
    raw_query: query,
  };
}

// ---------------------------------------------------------
// Helpers
// ---------------------------------------------------------

function normalizeQuery(query: string): string {
  return query
    .replace(/\s+/g, "")
    .replace(/[，。！？、；：,.!?;:]/g, " ")
    .trim();
}

interface TypedHit extends FeatureHit {
  atom_type: AtomType;
}

function findDictionaryHits(
  normalized: string,
  surfaceIndex: Map<string, AtomDictionaryEntry>,
): TypedHit[] {
  const hits: TypedHit[] = [];
  const seen = new Set<string>();

  // Longest-match first to avoid "自汗" being shadowed by "汗"
  const surfaces = Array.from(surfaceIndex.keys()).sort(
    (a, b) => b.length - a.length,
  );

  for (const surface of surfaces) {
    if (!normalized.includes(surface)) continue;
    const entry = surfaceIndex.get(surface);
    if (!entry) continue;

    const key = `${entry.atom_id}:${surface}`;
    if (seen.has(key)) continue;
    seen.add(key);

    hits.push({
      atom_id: entry.atom_id,
      canonical_name: entry.canonical_name,
      matched_surface: surface,
      match_type: surface === entry.canonical_name ? "canonical" : "alias",
      atom_type: entry.atom_type,
    });
  }

  return hits;
}

function stripAtomType(hits: TypedHit[]): FeatureHit[] {
  return hits.map(({ atom_type: _discard, ...rest }) => rest);
}

function detectMissingCategories(counts: {
  tongue: number;
  pulse: number;
  time: number;
}): MissingCategory[] {
  const missing: MissingCategory[] = [];
  if (counts.tongue === 0) missing.push("tongue_feature");
  if (counts.pulse === 0) missing.push("pulse_feature");
  if (counts.time === 0) missing.push("time_feature");
  return missing;
}

// ---------------------------------------------------------
// Convenience: format for answer assembly
// ---------------------------------------------------------

export function featuresToNormalizedQuery(features: ExtractedFeatures): {
  symptoms: string[];
  signs: string[];
  tongue_features: string[];
  pulse_features: string[];
  time_features: string[];
  location_hints: string[];
  pattern_hints: string[];
  missing: MissingCategory[];
} {
  return {
    symptoms: features.symptoms.map((h) => h.canonical_name),
    signs: features.signs.map((h) => h.canonical_name),
    tongue_features: features.tongue_features.map((h) => h.canonical_name),
    pulse_features: features.pulse_features.map((h) => h.canonical_name),
    time_features: features.time_features,
    location_hints: features.location_hints,
    pattern_hints: features.pattern_hints.map((h) => h.canonical_name),
    missing: features.missing,
  };
}
