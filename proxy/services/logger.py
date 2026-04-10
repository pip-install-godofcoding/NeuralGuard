import os
from typing import Optional

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


async def log_query(
    *,
    user_id: str,
    model_requested: str,
    model_used: str,
    prompt_snippet: str,
    token_usage: int,
    cost_usd: float,
    cost_saved_usd: float,
    cache_hit: bool,
    latency_ms: float,
) -> Optional[str]:
    """
    Log a query to Supabase query_logs.
    Returns the new row's UUID (needed for trust score updates), or None on failure.
    """
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = (
            supabase.table("query_logs")
            .insert(
                {
                    "user_id": user_id,
                    "model_requested": model_requested,
                    "model_used": model_used,
                    "prompt_snippet": prompt_snippet,
                    "token_usage": token_usage,
                    "cost_usd": float(cost_usd),
                    "cost_saved_usd": float(cost_saved_usd),
                    "cache_hit": cache_hit,
                    "latency_ms": float(latency_ms),
                }
            )
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
    except Exception as exc:
        print(f"[logger] Failed to log query: {exc}")

    return None
