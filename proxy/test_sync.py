import httpx, os, json
from dotenv import load_dotenv

load_dotenv("proxy/.env")

KEY = os.environ.get("GEMINI_API_KEY", "")

TRUST_PROMPT = """\
You are a factual accuracy evaluator. Given a user prompt and an AI response, rate the response's factual confidence on a scale of 0 to 100.

Rules:
- 90-100: Highly factual, well-grounded statements
- 70-89:  Mostly accurate, minor hedges or omissions
- 50-69:  Mixed accuracy, some unverifiable claims
- 0-49:   Speculative, likely incorrect, or hallucinated

Return ONLY valid JSON with no markdown:
{{"score": <int 0-100>, "reasoning": "<one concise sentence>"}}

User Prompt: Write an extremely detailed Wikipedia-style article about the devastating covid 19 pandemic.

AI Response: The COVID-19 pandemic, also known as the coronavirus pandemic, is a global pandemic of coronavirus disease 2019 (COVID-19) caused by severe acute respiratory syndrome coronavirus 2 (SARS-CoV-2)."""

data = {
    "model": "gemini-2.5-flash",
    "messages": [
        {"role": "user", "content": TRUST_PROMPT}
    ],
    "max_tokens": 120,
    "temperature": 0
}

r = httpx.post(
    "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    json=data,
    timeout=30.0
)
print("STATUS:", r.status_code)
print("RAW:", r.text)
