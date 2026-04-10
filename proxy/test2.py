import asyncio, os
from dotenv import load_dotenv
load_dotenv(".env")
from openai import AsyncOpenAI
_openai = AsyncOpenAI(api_key=os.environ.get("GEMINI_API_KEY", ""), base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

TRUST_PROMPT = """\
You are a factual accuracy evaluator. Given a user prompt and an AI response, rate the response's factual confidence on a scale of 0 to 100.

Rules:
- 90-100: Highly factual, well-grounded statements
- 70-89:  Mostly accurate, minor hedges or omissions
- 50-69:  Mixed accuracy, some unverifiable claims
- 0-49:   Speculative, likely incorrect, or hallucinated

Return ONLY valid JSON with no markdown:
{{"score": <int 0-100>, "reasoning": "<one concise sentence>"}}

User Prompt: Write an extremely detailed Wikipedia-style article about the devastating Pulwama attack in 2019.

AI Response: This article provides an extremely detailed, Wikipedia-style account of the 2019 Pulwama attack.
---
{{Infobox terrorist attack
| name           = 2019 Pulwama Attack
| date           = 14 February 2019"""

async def test():
    try:
        res = await _openai.chat.completions.create(model="gemini-2.5-flash", messages=[{"role": "user", "content": TRUST_PROMPT}], temperature=0)
        print("RESULT:")
        print(repr(res.choices[0].message.content))
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
