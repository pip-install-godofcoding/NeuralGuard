import asyncio, os
from dotenv import load_dotenv
load_dotenv(".env")
from openai import AsyncOpenAI
_openai = AsyncOpenAI(api_key=os.environ.get("GEMINI_API_KEY", ""), base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

TRUST_SYSTEM_PROMPT = """\
You are NeuralGuard, a strict factuality auditor. Your job is to detect hallucinations, not to be polite.

Process rules:
1) Extract concrete, checkable claims from the candidate response. Ignore opinions, style, and safe hedges.
2) For each claim, verify using ONLY:
    - the user's prompt,
    - the model's response,
    - any provided context (if included).
3) If a claim requires external knowledge and is not supported by the given context, mark it as UNSUPPORTED.
4) If a claim contradicts the prompt or provided context, mark it as CONTRADICTED.
5) If the response makes up sources, quotes, statistics, dates, or proper nouns not grounded in provided context, mark those as UNSUPPORTED.
6) Be adversarial: assume the answer might be wrong unless there is clear support.
7) Provide a compact per-claim verdict and evidence snippet from the provided context when supported.

Output must be valid JSON and follow the schema exactly. No extra keys, no markdown.
"""

TRUST_USER_PROMPT = """\
USER_PROMPT:
{prompt}

MODEL_RESPONSE:
{response}

CONTEXT (if any):
{context}
"""

async def test():
    p = "Write an extremely detailed Wikipedia-style article about the devastating Pulwama attack in 2019."
    r = """This article provides an extremely detailed, Wikipedia-style account of the 2019 Pulwama attack.

---

{{Infobox terrorist attack
| name           = 2019 Pulwama Attack
| image          = [[File:Pulwama_Attack_Aftermath.jpg|300px|alt=Burnt remains of vehicles, debris scattered on a highway.]]
| image_caption  = The aftermath of the Pulwama attack on National Highway 44
| date           = 14 February 2019"""
    res = await _openai.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {"role": "system", "content": TRUST_SYSTEM_PROMPT},
            {"role": "user", "content": TRUST_USER_PROMPT.format(prompt=p, response=r, context="")},
        ],
        temperature=0,
        max_tokens=600,
    )
    print("EVAL RESULT:")
    print(res.choices[0].message.content)

asyncio.run(test())
