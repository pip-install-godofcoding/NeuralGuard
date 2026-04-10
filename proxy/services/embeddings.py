import os

from openai import AsyncOpenAI

_client = AsyncOpenAI(
    api_key=os.environ.get("GEMINI_API_KEY", ""),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


async def embed_prompt(text: str) -> list[float]:
    """
    Generate a 768-dim embedding using gemini-embedding-2-preview.
    """
    resp = await _client.embeddings.create(
        model="gemini-embedding-2-preview",
        input=text[:8000],  # Hard cap
    )
    return resp.data[0].embedding
