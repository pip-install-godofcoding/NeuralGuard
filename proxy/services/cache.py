import json
import os
import uuid
from typing import Optional

import numpy as np
import redis.asyncio as aioredis

CACHE_PREFIX = "ng:cache:"
SIMILARITY_THRESHOLD = 0.78
TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
_redis_available: bool = True  # Innocent until proven guilty


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _get_redis() -> aioredis.Redis:
    """Create a fresh Redis client each time - avoids event loop issues on reload."""
    return aioredis.from_url(REDIS_URL, decode_responses=False)


async def init_redis():
    """Called once at startup to verify Redis is reachable."""
    global _redis_available
    try:
        r = _get_redis()
        await r.ping()
        await r.aclose()
        _redis_available = True
        print("[cache] Redis connected OK")
    except Exception as exc:
        _redis_available = False
        print(f"[cache] Redis unavailable - cache disabled: {exc}")


async def check_cache(embedding: list[float]) -> Optional[dict]:
    """
    Scan cached embeddings for cosine similarity >= threshold.
    Returns the cached response dict, or None.
    Fail-open: any error returns None.
    """
    if not _redis_available:
        return None

    try:
        r = _get_redis()
        best_sim = 0.0
        best_response = None

        async for key in r.scan_iter(f"{CACHE_PREFIX}*", count=500):
            raw = await r.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            sim = _cosine_similarity(embedding, entry["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_response = entry["response"]

        await r.aclose()
        print(f"[cache] Best similarity: {best_sim:.4f} (threshold: {SIMILARITY_THRESHOLD})")

        if best_sim >= SIMILARITY_THRESHOLD:
            print("[cache] HIT!")
            return best_response

    except Exception as e:
        print(f"[cache] check error: {e}")

    return None


async def store_cache(embedding: list[float], response: dict):
    """Store embedding + response in Redis with TTL."""
    if not _redis_available:
        return

    try:
        r = _get_redis()
        key = f"{CACHE_PREFIX}{uuid.uuid4().hex}"
        entry = {"embedding": embedding, "response": response}
        await r.setex(key, TTL_SECONDS, json.dumps(entry))
        await r.aclose()
        print(f"[cache] Stored key: {key[-8:]}")
    except Exception as e:
        print(f"[cache] store error: {e}")
