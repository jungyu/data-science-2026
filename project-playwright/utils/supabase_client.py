"""
Supabase Client 工廠。

提供統一的 Supabase 連線入口，使用 service_role key 繞過 RLS，
適合後端 worker（ch08 crawler pipeline）。

使用方式：
    from utils.supabase_client import get_supabase, get_crawler_table

    # 直接操作 crawler schema 的表
    db = get_crawler_table("articles")
    result = db.select("id, title").limit(10).execute()

    # 或取得 client 自行操作
    supabase = get_supabase()
    supabase.schema("crawler").table("sources").select("*").execute()

前置需求：
    .env 必須設定：
        SUPABASE_URL=https://your-project.supabase.co
        SUPABASE_SERVICE_KEY=eyJ...

    Supabase Dashboard → Settings → API → Extra schemas to expose:
        加入 crawler（讓 PostgREST 可以存取 crawler schema）

注意：
    service_role key 擁有完整的 DB 存取權，請勿暴露給前端或提交至版控。
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import AsyncClient, Client, create_async_client, create_client

load_dotenv()

_REQUIRED_ENV = ("SUPABASE_URL", "SUPABASE_SERVICE_KEY")


def _validate_env() -> tuple[str, str]:
    """檢查必要環境變數是否存在，回傳 (url, key)。"""
    missing = [k for k in _REQUIRED_ENV if not os.getenv(k)]
    if missing:
        raise EnvironmentError(
            f"缺少必要環境變數：{', '.join(missing)}\n"
            "請複製 .env.example 為 .env 並填入 Supabase 連線資訊。"
        )
    return os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """取得 Supabase client（singleton，首次呼叫時建立）。

    Returns:
        已連線的 Supabase Client（使用 service_role key）
    """
    url, key = _validate_env()
    return create_client(url, key)


_async_client: AsyncClient | None = None


async def get_async_supabase() -> AsyncClient:
    """取得 async Supabase client（singleton）。

    `create_async_client` 是 awaitable，所以無法直接套用 lru_cache。
    用模組層級變數快取首次建立的實例，供 ch09 等 async 腳本共用。
    """
    global _async_client
    if _async_client is None:
        url, key = _validate_env()
        _async_client = await create_async_client(url, key)
    return _async_client


def get_crawler_table(table_name: str):
    """取得 crawler schema 下指定資料表的 QueryBuilder。

    Args:
        table_name: 資料表名稱（不含 schema 前綴），例如 "articles"

    Returns:
        可直接呼叫 .select() / .insert() / .upsert() 的 QueryBuilder

    範例：
        result = get_crawler_table("sources").select("*").eq("is_enabled", True).execute()
    """
    return get_supabase().schema("crawler").table(table_name)
