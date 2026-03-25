-- ============================================================
-- 008: Storage Buckets — 檔案儲存 + RLS
-- ============================================================
-- Supabase Storage = S3-compatible object storage + RLS
--
-- 三個 bucket 對應三個業務場景：
--   1. product-images (shop)  — 商品圖片，公開讀取
--   2. crawler-assets (crawler) — 爬蟲截圖/附件，內部使用
--   3. rag-documents (rag)     — RAG 原始文件（PDF/MD），權限控制
--
-- 教學重點：
--   - storage.buckets = bucket 定義
--   - storage.objects = 檔案 metadata（RLS 在這裡）
--   - bucket 的 public = 是否允許匿名 GET（不需 auth token）
--   - RLS policy 控制誰能 upload / delete
--   - 搭配 shop.product_images.storage_path 做關聯
-- ============================================================


-- ============================================================
-- 1. BUCKETS
-- ============================================================

-- 1a. 商品圖片（公開讀取，staff 上傳）
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'product-images',
  'product-images',
  TRUE,                    -- 公開 = 不需 auth token 就能 GET
  5242880,                 -- 5MB 限制
  ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/svg+xml']
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 1b. 爬蟲截圖/資產（私有，service_role 存取）
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'crawler-assets',
  'crawler-assets',
  FALSE,                   -- 私有 = 需要 auth token
  10485760,                -- 10MB
  ARRAY['image/jpeg', 'image/png', 'image/webp', 'application/pdf', 'text/html']
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 1c. RAG 文件（私有，owner 控制）
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'rag-documents',
  'rag-documents',
  FALSE,
  52428800,                -- 50MB（PDF 可能較大）
  ARRAY[
    'application/pdf',
    'text/plain',
    'text/markdown',
    'text/html',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;


-- ============================================================
-- 2. STORAGE RLS POLICIES
-- ============================================================
-- storage.objects 的 RLS 結構：
--   - bucket_id: 哪個 bucket
--   - name: 檔案路徑（含資料夾）
--   - owner: 上傳者的 auth.uid()
--   - metadata: 自訂 metadata（JSONB）

-- ──────────────────────────────────────
-- 2a. product-images: 公開讀，staff 寫刪
-- ──────────────────────────────────────

-- 任何人都能讀（public bucket 也能直接 URL 存取，但 policy 仍需要）
CREATE POLICY "product_images_public_read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'product-images');

-- Staff 才能上傳
-- 路徑慣例：product-images/{product_id}/{filename}
CREATE POLICY "product_images_staff_upload"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'product-images'
    AND shop.is_staff()
  );

-- Staff 才能更新 metadata
CREATE POLICY "product_images_staff_update"
  ON storage.objects FOR UPDATE TO authenticated
  USING (
    bucket_id = 'product-images'
    AND shop.is_staff()
  );

-- Staff 才能刪除
CREATE POLICY "product_images_staff_delete"
  ON storage.objects FOR DELETE TO authenticated
  USING (
    bucket_id = 'product-images'
    AND shop.is_staff()
  );

-- ──────────────────────────────────────
-- 2b. crawler-assets: service_role only + authenticated 讀
-- ──────────────────────────────────────

-- Authenticated 使用者可讀（內部後台檢視截圖）
CREATE POLICY "crawler_assets_auth_read"
  ON storage.objects FOR SELECT TO authenticated
  USING (bucket_id = 'crawler-assets');

-- 只有 service_role 可寫（crawler worker 用 service key）
CREATE POLICY "crawler_assets_service_write"
  ON storage.objects FOR INSERT TO service_role
  WITH CHECK (bucket_id = 'crawler-assets');

CREATE POLICY "crawler_assets_service_update"
  ON storage.objects FOR UPDATE TO service_role
  USING (bucket_id = 'crawler-assets');

CREATE POLICY "crawler_assets_service_delete"
  ON storage.objects FOR DELETE TO service_role
  USING (bucket_id = 'crawler-assets');

-- ──────────────────────────────────────
-- 2c. rag-documents: owner 讀寫，公開 collection 可讀
-- ──────────────────────────────────────

-- 路徑慣例：rag-documents/{collection_id}/{document_id}/{filename}
-- 讀取：文件 owner 或 active collection 的成員
CREATE POLICY "rag_documents_read"
  ON storage.objects FOR SELECT TO authenticated
  USING (
    bucket_id = 'rag-documents'
    AND (
      -- owner 可讀自己的
      (storage.foldername(name))[1] IN (
        SELECT c.id FROM rag.collections c
        WHERE c.owner_id = (SELECT auth.uid())::TEXT
      )
      -- active collection 的文件公開可讀
      OR (storage.foldername(name))[1] IN (
        SELECT c.id FROM rag.collections c WHERE c.is_active = TRUE
      )
    )
  );

-- 上傳：只有 collection owner
CREATE POLICY "rag_documents_upload"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'rag-documents'
    AND (storage.foldername(name))[1] IN (
      SELECT c.id FROM rag.collections c
      WHERE c.owner_id = (SELECT auth.uid())::TEXT
    )
  );

-- 刪除：只有 collection owner
CREATE POLICY "rag_documents_delete"
  ON storage.objects FOR DELETE TO authenticated
  USING (
    bucket_id = 'rag-documents'
    AND (storage.foldername(name))[1] IN (
      SELECT c.id FROM rag.collections c
      WHERE c.owner_id = (SELECT auth.uid())::TEXT
    )
  );

-- service_role 對所有 bucket 都有完整權限（已內建，不需額外 policy）


-- ============================================================
-- 3. HELPER FUNCTIONS（Storage URL 產生）
-- ============================================================

-- 3a. 產生商品圖片的公開 URL
CREATE OR REPLACE FUNCTION public.api_shop_image_url(p_storage_path TEXT)
RETURNS TEXT
LANGUAGE SQL
IMMUTABLE
AS $$
  -- Supabase Storage 公開 URL 格式
  -- 實際部署時 replace with your project URL
  SELECT '/storage/v1/object/public/product-images/' || p_storage_path;
$$;

-- 3b. 產生已簽名的私有 URL（示範用，實際用 SDK）
-- 注意：真正的 signed URL 需要 service_role key，不能在 SQL 產生
-- 這個 function 只是回傳路徑，讓前端知道去哪裡要 signed URL
CREATE OR REPLACE FUNCTION public.api_storage_path(
  p_bucket TEXT,
  p_path   TEXT
)
RETURNS TEXT
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT p_bucket || '/' || p_path;
$$;

GRANT EXECUTE ON FUNCTION public.api_shop_image_url(TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_storage_path(TEXT, TEXT) TO authenticated;


-- ============================================================
-- 4. 前端使用範例（TypeScript）
-- ============================================================
--
-- === 4a. 上傳商品圖片 ===
--
--   const { data, error } = await supabase.storage
--     .from('product-images')
--     .upload(`${productId}/${file.name}`, file, {
--       contentType: file.type,
--       upsert: true,  // 同名覆蓋
--     })
--
--   // 取得公開 URL
--   const { data: { publicUrl } } = supabase.storage
--     .from('product-images')
--     .getPublicUrl(`${productId}/${file.name}`)
--
--
-- === 4b. 上傳 RAG 文件 ===
--
--   const { data, error } = await supabase.storage
--     .from('rag-documents')
--     .upload(`${collectionId}/${documentId}/${file.name}`, file, {
--       contentType: file.type,
--     })
--
--   // 取得 signed URL（私有 bucket 需要）
--   const { data: { signedUrl } } = await supabase.storage
--     .from('rag-documents')
--     .createSignedUrl(`${collectionId}/${documentId}/${file.name}`, 3600)
--
--
-- === 4c. Crawler 截圖（server-side，用 service key） ===
--
--   // Python / Node.js backend
--   const { data, error } = await supabaseAdmin.storage
--     .from('crawler-assets')
--     .upload(`screenshots/${sourceId}/${Date.now()}.png`, screenshotBuffer, {
--       contentType: 'image/png',
--     })


-- ============================================================
-- 5. 確認 Bucket 設定
-- ============================================================
-- SELECT id, name, public, file_size_limit, allowed_mime_types
-- FROM storage.buckets
-- ORDER BY id;
--
-- 預期結果：
--   crawler-assets  | FALSE | 10485760
--   product-images  | TRUE  |  5242880
--   rag-documents   | FALSE | 52428800
