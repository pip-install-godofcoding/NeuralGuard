import hashlib
import os

from fastapi import HTTPException
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

_client: Client | None = None


def _supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def validate_key(raw_key: str) -> str:
    """
    Validate a NeuralGuard API key.
    Returns the associated user_id, or raises HTTP 401.
    """
    key_hash = _hash_key(raw_key)
    try:
        result = (
            _supabase()
            .table("api_keys")
            .select("user_id, is_active")
            .eq("key_hash", key_hash)
            .single()
            .execute()
        )
    except Exception as exc:
        if "PGRST116" in str(exc):
            raise HTTPException(401, "Invalid API key")
        raise HTTPException(401, f"Auth service unavailable: {exc}")

    if not result.data:
        raise HTTPException(401, "Invalid API key")

    if not result.data.get("is_active"):
        raise HTTPException(401, "API key has been revoked")

    return result.data["user_id"]
