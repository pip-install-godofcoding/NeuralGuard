import json
import os
import uuid
from typing import Optional

import numpy as np
import redis.asyncio as aioredis

CACHE_PREFIX = "ng:cache:"
SIMILARITY_THRESHOLD = 0.90
TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

_redis: aioredis.Redis | None = None


async def init_redis():
    """Called once at app startup."""
    global _redis
    try:
        _redis = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379"),
            decode_responses=False,
        )
        await _redis.ping()
        print("[cache] Redis connected ✓")
    except Exception as exc:
        print(f"[cache] Redis unavailable — cache disabled: {exc}")
        _redis = None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


async def check_cache(embedding: list[float]) -> Optional[dict]:
    """
    Scan cached embeddings for cosine similarity >= threshold.
    Returns the cached response dict, or None.
    Fail-open: any error returns None.
    """
    if _redis is None:
        return None

    try:
        best_sim = 0.0
        best_response = None

        async for key in _redis.scan_iter(f"{CACHE_PREFIX}*", count=500):
            raw = await _redis.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            sim = _cosine_similarity(embedding, entry["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_response = entry["response"]

        if best_sim >= SIMILARITY_THRESHOLD:
            return best_response
    except Exception:
        pass  # Fail open

    return None


async def store_cache(embedding: list[float], response: dict):
    """Store embedding + response in Redis with TTL."""
    if _redis is None:
        return

    try:
        key = f"{CACHE_PREFIX}{uuid.uuid4().hex}"
        entry = {"embedding": embedding, "response": response}
        await _redis.setex(key, TTL_SECONDS, json.dumps(entry))
    except Exception:
        pass  # Fail open
