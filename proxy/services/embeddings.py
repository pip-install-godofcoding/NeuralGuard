import os
import httpx

async def embed_prompt(text: str) -> list[float]:
    """
    Generate 384-dim semantic embeddings using Hugging Face Serverless API.
    Uses sentence-transformers/all-MiniLM-L6-v2.
    """
    hf_token = os.environ.get("HUGGINGFACE_API_KEY", "")
    if not hf_token or hf_token.startswith("your_"):
        print("[embed] WARNING: HUGGINGFACE_API_KEY not set, skipping cache")
        return [0.0] * 384
        
    url = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": text}
    
    print(f"[embed] Calling HF API...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], list):
                print(f"[embed] Got nested list, dim={len(data[0])}")
                return data[0]
            print(f"[embed] Got flat list, dim={len(data)}")
            return data
            
        raise ValueError(f"Unexpected response from HF API: {data}")
