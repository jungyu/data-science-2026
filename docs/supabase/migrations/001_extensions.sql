-- ============================================================
-- 001: Shared Extensions, Schemas & Utility Functions
-- ============================================================
-- 所有 schema 共用的基礎設施，必須最先執行。
--
-- 執行順序：
--   001_extensions.sql        ← 你在這裡
--   002_shop_schema.sql
--   003_crawler_schema.sql
--   004_rag_schema.sql
--   005_analytics_schema.sql  ← 依賴 002-004
--   006_public_api.sql        ← 依賴 002-005
-- ============================================================


-- ============================================================
-- 1. SCHEMAS
-- ============================================================
CREATE SCHEMA IF NOT EXISTS shop;
CREATE SCHEMA IF NOT EXISTS crawler;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS analytics;


-- ============================================================
-- 2. EXTENSIONS
-- ============================================================
-- 放在 extensions schema（Supabase 預設），所有 schema 共用。
CREATE EXTENSION IF NOT EXISTS pgcrypto;       -- gen_random_bytes (ULID)
CREATE EXTENSION IF NOT EXISTS moddatetime;    -- updated_at triggers
CREATE EXTENSION IF NOT EXISTS pg_trgm;        -- trigram search (shop, crawler)
CREATE EXTENSION IF NOT EXISTS vector;         -- pgvector (rag)


-- ============================================================
-- 3. ULID GENERATOR（全域共用）
-- ============================================================
-- 26-char Crockford Base32, time-sortable.
-- 放在 public schema，所有 schema 的 PK DEFAULT 統一引用 public.generate_ulid()。
-- 不再每個 schema 各放一份。

CREATE OR REPLACE FUNCTION public.generate_ulid()
RETURNS TEXT
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
  unix_ts    BIGINT;
  output     TEXT := '';
  encoding   CHAR[] := string_to_array('0123456789ABCDEFGHJKMNPQRSTVWXYZ', NULL);
  i          INTEGER;
  rand_bytes BYTEA;
BEGIN
  unix_ts := (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT;
  -- Encode 48-bit timestamp (10 chars)
  FOR i IN REVERSE 9..0 LOOP
    output := output || encoding[1 + (unix_ts % 32)::INT];
    unix_ts := unix_ts >> 5;
  END LOOP;
  -- Encode 80-bit random (16 chars)
  rand_bytes := gen_random_bytes(10);
  FOR i IN 0..9 LOOP
    output := output || encoding[1 + (get_byte(rand_bytes, i) % 32)];
  END LOOP;
  RETURN output;
END;
$$;

GRANT EXECUTE ON FUNCTION public.generate_ulid() TO authenticated, anon, service_role;
