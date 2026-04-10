import asyncio
import os
import time

import httpx
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse

from services.auth import validate_key
from services.cache import check_cache, store_cache
from services.embeddings import embed_prompt
from services.logger import log_query
from services.model_router import route_model, estimate_cost
from services.trust import evaluate_trust

router = APIRouter(tags=["proxy"])

OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")


# ─────────────────────────────────────────────────────────────
# Main proxy endpoint
# ─────────────────────────────────────────────────────────────
@router.post("/chat/completions")
async def chat_completions(request: Request, background_tasks: BackgroundTasks):
    start = time.perf_counter()

    # ── 1. Auth ────────────────────────────────────────────────
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or malformed Authorization header")

    user_id = await validate_key(auth_header[7:])

    # ── 2. Parse body ──────────────────────────────────────────
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    messages = body.get("messages", [])
    model_requested = body.get("model", "gemini-2.5-flash")
    is_stream = body.get("stream", False)

    # Flatten user messages for caching / routing
    prompt_text = " ".join(
        m.get("content", "") for m in messages if m.get("role") == "user"
    )

    # ── 3. Heuristic routing ───────────────────────────────────
    model_used, cost_saved = route_model(model_requested, prompt_text)
    body["model"] = model_used

    # ── 4. Semantic cache (non-streaming only) ─────────────────
    embedding = None
    if not is_stream:
        try:
            embedding = await embed_prompt(prompt_text)
            cached = await check_cache(embedding)
            if cached is not None:
                elapsed_ms = (time.perf_counter() - start) * 1000
                asyncio.create_task(
                    log_query(
                        user_id=user_id,
                        model_requested=model_requested,
                        model_used=model_used,
                        prompt_snippet=prompt_text[:200],
                        token_usage=0,
                        cost_usd=0.0,
                        cost_saved_usd=cost_saved,
                        cache_hit=True,
                        latency_ms=elapsed_ms,
                    )
                )
                return JSONResponse(cached)
        except Exception:
            pass  # Fail open — proceed to LLM

    # ── 5. Forward to OpenAI ───────────────────────────────────
    headers = {
        "Authorization": f"Bearer {GEMINI_KEY}",
        "Content-Type": "application/json",
    }

    if is_stream:
        return await _stream_response(
            body, headers, user_id, model_requested, model_used,
            prompt_text, cost_saved, start
        )

    # Non-streaming path
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OPENAI_BASE}/chat/completions", json=body, headers=headers
            )
    except httpx.TimeoutException:
        raise HTTPException(504, "Upstream LLM timed out")

    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Gemini error: {resp.text[:500]}")

    data = resp.json()
    elapsed_ms = (time.perf_counter() - start) * 1000
    usage = data.get("usage", {})
    token_usage = usage.get("total_tokens", 0)
    cost_usd = estimate_cost(model_used, usage)

    # ── 6. Cache the result ────────────────────────────────────
    if embedding is not None:
        try:
            await store_cache(embedding, data)
        except Exception:
            pass  # Fail open

    # ── 7. Async log + trust scoring ──────────────────────────
    query_id = await log_query(
        user_id=user_id,
        model_requested=model_requested,
        model_used=model_used,
        prompt_snippet=prompt_text[:200],
        token_usage=token_usage,
        cost_usd=cost_usd,
        cost_saved_usd=cost_saved,
        cache_hit=False,
        latency_ms=elapsed_ms,
    )

    response_text = (
        data.get("choices", [{}])[0].get("message", {}).get("content", "")
    )
    if query_id and response_text:
        background_tasks.add_task(evaluate_trust, query_id, prompt_text, response_text)

    return JSONResponse(data)


# ─────────────────────────────────────────────────────────────
# Streaming helper
# ─────────────────────────────────────────────────────────────
async def _stream_response(
    body: dict,
    headers: dict,
    user_id: str,
    model_requested: str,
    model_used: str,
    prompt_text: str,
    cost_saved: float,
    start: float,
):
    async def _generator():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{OPENAI_BASE}/chat/completions",
                    json=body, headers=headers
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            asyncio.create_task(
                log_query(
                    user_id=user_id,
                    model_requested=model_requested,
                    model_used=model_used,
                    prompt_snippet=prompt_text[:200],
                    token_usage=0,
                    cost_usd=0.0,
                    cost_saved_usd=cost_saved,
                    cache_hit=False,
                    latency_ms=elapsed_ms,
                )
            )

    return StreamingResponse(_generator(), media_type="text/event-stream")
