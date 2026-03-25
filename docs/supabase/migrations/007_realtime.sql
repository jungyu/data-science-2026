-- ============================================================
-- 007: Realtime — 即時訂閱與廣播
-- ============================================================
-- Supabase Realtime 三種模式：
--   1. Postgres Changes — 監聽表的 INSERT/UPDATE/DELETE
--   2. Broadcast — 低延遲 pub/sub（不經 DB）
--   3. Presence — 線上狀態追蹤
--
-- 本檔只處理 Postgres Changes（需要 DDL）。
-- Broadcast / Presence 是純前端 SDK 操作，不需要 migration。
--
-- 教學重點：
--   - 只在「真正需要即時」的表啟用，不要全開（效能考量）
--   - Realtime 走 WAL → Publication → WebSocket，每張表都有成本
--   - 搭配 RLS：Realtime 會尊重 RLS policy，未授權的 row 不會推送
-- ============================================================


-- ============================================================
-- 1. 啟用 Realtime Publication
-- ============================================================
-- Supabase 預設有一個 publication: supabase_realtime
-- 把需要即時監聽的表加進去

-- Shop: 訂單狀態即時更新（顧客追蹤、後台管理）
ALTER PUBLICATION supabase_realtime ADD TABLE shop.orders;

-- Shop: 庫存變動即時通知（低庫存警告）
ALTER PUBLICATION supabase_realtime ADD TABLE shop.stocks;

-- Shop: 付款狀態（結帳流程即時回饋）
ALTER PUBLICATION supabase_realtime ADD TABLE shop.payments;

-- Shop: 新評論通知
ALTER PUBLICATION supabase_realtime ADD TABLE shop.reviews;

-- Crawler: 執行進度監控
ALTER PUBLICATION supabase_realtime ADD TABLE crawler.crawl_runs;

-- Crawler: 佇列狀態（worker 搶工作）
ALTER PUBLICATION supabase_realtime ADD TABLE crawler.crawl_queue;

-- RAG: 文件處理進度（上傳 → 解析 → 切片 → 嵌入）
ALTER PUBLICATION supabase_realtime ADD TABLE rag.documents;

-- Analytics: 事件流（即時儀表板）
ALTER PUBLICATION supabase_realtime ADD TABLE analytics.events;


-- ============================================================
-- 2. 確認 Publication 設定
-- ============================================================
-- 執行後用這個查詢確認：
--
-- SELECT schemaname, tablename
-- FROM pg_publication_tables
-- WHERE pubname = 'supabase_realtime'
-- ORDER BY schemaname, tablename;
--
-- 預期結果：
--   analytics | events
--   crawler   | crawl_queue
--   crawler   | crawl_runs
--   rag       | documents
--   shop      | orders
--   shop      | payments
--   shop      | reviews
--   shop      | stocks


-- ============================================================
-- 3. 前端使用範例（TypeScript）
-- ============================================================
-- 以下是前端程式碼範例，不是 SQL。放在註解裡供教學參考。
--
-- === 3a. 訂閱訂單狀態變更 ===
--
--   const channel = supabase
--     .channel('order-updates')
--     .on(
--       'postgres_changes',
--       {
--         event: 'UPDATE',
--         schema: 'shop',
--         table: 'orders',
--         filter: `customer_id=eq.${userId}`,
--       },
--       (payload) => {
--         console.log('訂單狀態變更:', payload.new.status)
--         // 更新 UI：pending → confirmed → shipped → delivered
--       }
--     )
--     .subscribe()
--
--
-- === 3b. 監聽庫存低水位警告 ===
--
--   const channel = supabase
--     .channel('stock-alerts')
--     .on(
--       'postgres_changes',
--       {
--         event: 'UPDATE',
--         schema: 'shop',
--         table: 'stocks',
--       },
--       (payload) => {
--         const { quantity, low_stock_threshold } = payload.new
--         if (low_stock_threshold && quantity <= low_stock_threshold) {
--           showAlert(`庫存低於 ${low_stock_threshold}！剩餘 ${quantity}`)
--         }
--       }
--     )
--     .subscribe()
--
--
-- === 3c. 追蹤 Crawler 執行進度 ===
--
--   const channel = supabase
--     .channel('crawl-progress')
--     .on(
--       'postgres_changes',
--       {
--         event: '*',           // INSERT + UPDATE
--         schema: 'crawler',
--         table: 'crawl_runs',
--       },
--       (payload) => {
--         updateProgressBar({
--           status: payload.new.run_status,
--           pages: payload.new.pages_fetched,
--           articles: payload.new.articles_extracted,
--           errors: payload.new.error_count,
--         })
--       }
--     )
--     .subscribe()
--
--
-- === 3d. RAG 文件處理進度（上傳後等待 embedding） ===
--
--   const channel = supabase
--     .channel('doc-processing')
--     .on(
--       'postgres_changes',
--       {
--         event: 'UPDATE',
--         schema: 'rag',
--         table: 'documents',
--         filter: `id=eq.${documentId}`,
--       },
--       (payload) => {
--         const status = payload.new.process_status
--         // uploaded → parsed → chunked → embedded → ready
--         updateProcessingStep(status)
--         if (status === 'ready') {
--           showSuccess('文件已就緒，可以開始搜尋！')
--           channel.unsubscribe()
--         } else if (status === 'failed') {
--           showError(payload.new.process_error)
--           channel.unsubscribe()
--         }
--       }
--     )
--     .subscribe()
--
--
-- === 3e. Broadcast 範例（不經 DB，純 WebSocket） ===
--
--   // 發送端（例如：管理員通知）
--   supabase.channel('announcements').send({
--     type: 'broadcast',
--     event: 'maintenance',
--     payload: { message: '系統將於 10 分鐘後維護' },
--   })
--
--   // 接收端
--   supabase
--     .channel('announcements')
--     .on('broadcast', { event: 'maintenance' }, (payload) => {
--       showBanner(payload.payload.message)
--     })
--     .subscribe()
--
--
-- === 3f. Presence 範例（線上狀態） ===
--
--   const channel = supabase.channel('online-users')
--
--   channel
--     .on('presence', { event: 'sync' }, () => {
--       const state = channel.presenceState()
--       updateOnlineUsers(Object.keys(state).length)
--     })
--     .subscribe(async (status) => {
--       if (status === 'SUBSCRIBED') {
--         await channel.track({
--           user_id: currentUser.id,
--           username: currentUser.username,
--           online_at: new Date().toISOString(),
--         })
--       }
--     })


-- ============================================================
-- 4. 移除 Realtime（如需停用）
-- ============================================================
-- ALTER PUBLICATION supabase_realtime DROP TABLE shop.reviews;
--
-- 確認移除：
-- SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';
