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

XAI_BASE = "https://api.groq.com/openai/v1"
SARVAM_BASE = "https://api.sarvam.ai/v1"
XAI_KEY = os.environ.get("XAI_API_KEY", "")
SARVAM_KEY = os.environ.get("SARVAM_API_KEY", "")


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
            print(f"[DEBUG] Embedding generated, dim={len(embedding)}, first3={embedding[:3]}")
            cached = await check_cache(embedding)
            if cached is not None:
                print("[DEBUG] CACHE HIT!")
                elapsed_ms = (time.perf_counter() - start) * 1000
                background_tasks.add_task(
                    log_query,
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
                return JSONResponse(cached)
            print("[DEBUG] Cache miss, proceeding to LLM")
        except Exception as e:
            print(f"[DEBUG] Cache/embed error: {e}")
            pass  # Fail open — proceed to LLM

    # ── 5. Forward to Upstream API ───────────────────────────────────
    if "sarvam" in model_used.lower():
        api_base = SARVAM_BASE
        headers = {
            "Authorization": f"Bearer {SARVAM_KEY}",
            "api-subscription-key": SARVAM_KEY,  # Added for safety with Sarvam
            "Content-Type": "application/json",
        }
    else:
        api_base = XAI_BASE
        headers = {
            "Authorization": f"Bearer {XAI_KEY}",
            "Content-Type": "application/json",
        }

    if is_stream:
        return await _stream_response(
            body, headers, user_id, model_requested, model_used,
            prompt_text, cost_saved, start, background_tasks, api_base
        )

    # Non-streaming path with retry for 503 errors (high demand)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions", json=body, headers=headers
                )
            
            if resp.status_code == 200:
                break
            
            if resp.status_code in (503, 500, 429) and attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                continue
                
            raise HTTPException(resp.status_code, f"Upstream API error: {resp.text[:500]}")
            
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise HTTPException(504, "Upstream LLM timed out")
    
    data = resp.json()
    elapsed_ms = (time.perf_counter() - start) * 1000
    usage = data.get("usage", {})
    token_usage = usage.get("total_tokens", 0)
    cost_usd = estimate_cost(model_used, usage)

    # ── 6. Cache the result ────────────────────────────────────
    if embedding is not None:
        try:
            print(f"[DEBUG] Storing to cache... Redis available: {embedding is not None}")
            await store_cache(embedding, data)
            print("[DEBUG] Cache stored OK")
        except Exception as e:
            print(f"[DEBUG] Cache store error: {e}")
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
    background_tasks: BackgroundTasks,
    api_base: str,
):
    collected_chunks: list[bytes] = []

    async def _generator():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{api_base}/chat/completions",
                    json=body, headers=headers
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        collected_chunks.append(chunk)
                        yield chunk
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Extract text from SSE chunks: look for delta content fields
            import json as _json
            response_text_parts: list[str] = []
            for raw_chunk in collected_chunks:
                for line in raw_chunk.decode("utf-8", errors="ignore").splitlines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk_data = _json.loads(line[6:])
                            delta = chunk_data["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                response_text_parts.append(delta["content"])
                        except Exception:
                            pass
            response_text = "".join(response_text_parts)

            query_id = await log_query(
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

            # ── Fire trust evaluation for streamed responses ──────────
            if query_id and response_text:
                background_tasks.add_task(
                    evaluate_trust, query_id, prompt_text, response_text
                )

    return StreamingResponse(_generator(), media_type="text/event-stream")
