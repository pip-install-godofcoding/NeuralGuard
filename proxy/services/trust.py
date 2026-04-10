import json
import os

import re

from openai import AsyncOpenAI
from supabase import create_client

_openai = AsyncOpenAI(
    api_key=os.environ.get("GEMINI_API_KEY", ""),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

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

Schema:
{
    "claims": [
        {
            "id": "c1",
            "claim": "string",
            "verdict": "SUPPORTED | UNSUPPORTED | CONTRADICTED | NOT_APPLICABLE",
            "support": "short evidence snippet or 'none'",
            "reason": "short explanation"
        }
    ],
    "summary": {
        "supported": 0,
        "unsupported": 0,
        "contradicted": 0,
        "not_applicable": 0,
        "hallucination_risk": "LOW | MEDIUM | HIGH"
    }
}
"""

TRUST_USER_PROMPT = """\
USER_PROMPT:
{prompt}

MODEL_RESPONSE:
{response}

CONTEXT (if any):
{context}
"""

DEFAULT_TRUST_SCORE = 50


def _extract_json(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


def _derive_score(details: dict) -> int:
    claims = details.get("claims", []) if isinstance(details, dict) else []
    if not isinstance(claims, list):
        return DEFAULT_TRUST_SCORE

    total = len(claims)
    if total == 0:
        return DEFAULT_TRUST_SCORE

    unsupported = 0
    contradicted = 0
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        verdict = str(claim.get("verdict", "")).upper()
        if verdict == "UNSUPPORTED":
            unsupported += 1
        elif verdict == "CONTRADICTED":
            contradicted += 1

    penalty = (unsupported * 15) + (contradicted * 35)
    score = int(round(100 - (penalty / max(1, total))))
    return max(0, min(100, score))


def _ensure_summary(details: dict) -> dict:
    if not isinstance(details, dict):
        return details
    claims = details.get("claims", []) if isinstance(details.get("claims", []), list) else []

    supported = 0
    unsupported = 0
    contradicted = 0
    not_applicable = 0
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        verdict = str(claim.get("verdict", "")).upper()
        if verdict == "SUPPORTED":
            supported += 1
        elif verdict == "UNSUPPORTED":
            unsupported += 1
        elif verdict == "CONTRADICTED":
            contradicted += 1
        elif verdict == "NOT_APPLICABLE":
            not_applicable += 1

    total = max(1, len(claims))
    unsupported_ratio = (unsupported + contradicted) / total
    if contradicted > 0 or unsupported_ratio > 0.3:
        risk = "HIGH"
    elif unsupported_ratio > 0.1:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    details["summary"] = {
        "supported": supported,
        "unsupported": unsupported,
        "contradicted": contradicted,
        "not_applicable": not_applicable,
        "hallucination_risk": risk,
    }
    return details


async def evaluate_trust(query_id: str, prompt: str, response: str, context: str = ""):
    """
    Background task: call gemini-2.5-flash to score the response,
    then update the query_logs row. Completely fail-silent.
    """
    try:
        result = await _openai.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {
                    "role": "system",
                    "content": TRUST_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": TRUST_USER_PROMPT.format(
                        prompt=prompt[:700],
                        response=response[:2200],
                        context=context[:1200],
                    ),
                }
            ],
            temperature=0,
            max_tokens=600,
        )

        raw = result.choices[0].message.content.strip()
        details = _extract_json(raw) or {}
        details = _ensure_summary(details)
        score = _derive_score(details)

        supabase = create_client(
            os.environ.get("SUPABASE_URL", ""),
            os.environ.get("SUPABASE_SERVICE_KEY", ""),
        )
        payload = {"trust_score": score}
        if details:
            payload["trust_details"] = details

        try:
            supabase.table("query_logs").update(payload).eq("id", query_id).execute()
        except Exception:
            if "trust_details" in payload:
                supabase.table("query_logs").update({"trust_score": score}).eq(
                    "id", query_id
                ).execute()

    except Exception as e:
        import sys
        print(f"TRUST EVAL ERROR: {e}\nRAW REASON: {repr(raw) if 'raw' in locals() else 'None'}", file=sys.stderr)
