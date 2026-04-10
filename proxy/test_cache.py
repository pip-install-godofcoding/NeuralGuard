"""
Quick cache diagnostic - run from proxy/ directory:
  python test_cache.py
"""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

async def main():
    # 1. Test embeddings
    print("=== EMBEDDING TEST ===")
    hf_key = os.environ.get("HUGGINGFACE_API_KEY", "")
    print(f"HF key loaded: {hf_key[:12]}..." if hf_key else "HF key: MISSING!")

    from services.embeddings import embed_prompt
    p1 = "Can you make a short 2-line rhyme about coding in Python?"
    p2 = "Please write me a quick two line rhyming poem about Python programming."

    print(f"\nEmbedding prompt 1...")
    e1 = await embed_prompt(p1)
    print(f"  dim={len(e1)}, all_zeros={all(v==0 for v in e1)}, first3={e1[:3]}")

    print(f"Embedding prompt 2...")
    e2 = await embed_prompt(p2)
    print(f"  dim={len(e2)}, all_zeros={all(v==0 for v in e2)}, first3={e2[:3]}")

    import numpy as np
    va, vb = np.array(e1), np.array(e2)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    sim = float(np.dot(va, vb) / denom) if denom else 0.0
    print(f"\nCosine similarity: {sim:.4f} (threshold: 0.78)")
    print(f"Will cache hit? {sim >= 0.78}")

    # 2. Test Redis
    print("\n=== REDIS TEST ===")
    from services.cache import init_redis, store_cache, check_cache
    await init_redis()

    print("Storing embedding 1...")
    await store_cache(e1, {"choices": [{"message": {"content": "CACHED RESPONSE"}}]})

    print("Checking for embedding 2 (should hit if sim >= 0.78)...")
    hit = await check_cache(e2)
    print(f"Cache hit: {hit is not None}")
    if hit:
        print(f"Returned: {hit}")

asyncio.run(main())
