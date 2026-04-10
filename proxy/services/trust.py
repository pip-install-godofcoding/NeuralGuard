import json
import os
import re
import sys

from openai import AsyncOpenAI
from supabase import create_client

_openai = AsyncOpenAI(
    api_key=os.environ.get("XAI_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1"
)

# ─── Prompts ────────────────────────────────────────────────────────────────

TRUST_SYSTEM_PROMPT = """\
You are NeuralGuard Auditor v2, a hostile factuality verifier. Your ONLY job is to find hallucinations.
You have a strong prior that the response might contain errors. You are NOT trying to be helpful — you are trying to catch mistakes.

━━━ STAGE 1 — DECONSTRUCT ━━━
Extract every atomic, falsifiable claim from the MODEL_RESPONSE.
- A claim is a single discrete assertion that could independently be true or false.
- Ignore: opinions, subjective descriptions, hedged statements ("it might be", "some argue"), filler text.
- Include: dates, numbers, names, locations, causal relationships, quotes, statistics, technical facts.
- Assign each claim a type from: [FACTUAL_DATE, FACTUAL_NUMBER, FACTUAL_NAME, CAUSAL, TECHNICAL, QUOTE, OTHER]

━━━ STAGE 2 — VERIFY ADVERSARIALLY ━━━
For each claim, ask yourself:
  Q1: Is this claim verifiable using ONLY the USER_PROMPT and provided CONTEXT?
      If NO → mark UNSUPPORTED immediately. Do not speculate using your own knowledge.
  Q2: Does this claim contradict anything in the USER_PROMPT or CONTEXT?
      If YES → mark CONTRADICTED.
  Q3: Does the response assert specific numbers, names, or dates not present in CONTEXT?
      If YES → these are HIGH-RISK UNSUPPORTED claims.

FORBIDDEN BEHAVIORS (you MUST avoid these):
  ✗ Giving SUPPORTED verdicts to claims just because they "sound right"
  ✗ Using your own parametric knowledge to "fill in" missing context
  ✗ Merging multiple separate claims into one (keep every claim atomic)
  ✗ Marking numbers/dates/proper nouns as SUPPORTED unless they appear verbatim in CONTEXT

━━━ STAGE 3 — WEIGH SEVERITY ━━━
For each UNSUPPORTED or CONTRADICTED claim, assign severity:
  CRITICAL  → a specific factual assertion (number, date, name) that is wrong/unverified
  MAJOR     → a causal or definitional claim that is wrong/unverified
  MINOR     → a vague generalization that cannot be verified but is low-stakes
  N/A       → use for SUPPORTED or NOT_APPLICABLE verdicts

━━━ STAGE 4 — INTERNAL CONSISTENCY CHECK ━━━
Re-read the entire MODEL_RESPONSE and answer:
  - Does the response contradict itself in any two parts? (self_contradiction: true/false)
  - Does the response over-hedge, hiding uncertainty with vague language? (over_hedging: true/false)
  - Does the response contain unsupported causal chains (A causes B causes C)? (causal_chain_risk: true/false)

━━━ OUTPUT FORMAT ━━━
Respond with VALID JSON only. No markdown, no prose outside JSON.

{
  "claims": [
    {
      "id": "c1",
      "claim": "string — exact atomic assertion",
      "claim_type": "FACTUAL_DATE | FACTUAL_NUMBER | FACTUAL_NAME | CAUSAL | TECHNICAL | QUOTE | OTHER",
      "verdict": "SUPPORTED | UNSUPPORTED | CONTRADICTED | NOT_APPLICABLE",
      "severity": "CRITICAL | MAJOR | MINOR | N/A",
      "support": "verbatim snippet from CONTEXT proving this, or 'none'",
      "reason": "one-sentence explanation"
    }
  ],
  "consistency": {
    "self_contradiction": false,
    "over_hedging": false,
    "causal_chain_risk": false
  },
  "summary": {
    "supported": 0,
    "unsupported": 0,
    "contradicted": 0,
    "not_applicable": 0,
    "critical_count": 0,
    "hallucination_risk": "LOW | MEDIUM | HIGH | CRITICAL"
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

# ─── Constants ───────────────────────────────────────────────────────────────

DEFAULT_TRUST_SCORE = 50

# Per-severity base penalty points
SEVERITY_PENALTY = {
    "CRITICAL": 40,
    "MAJOR":    20,
    "MINOR":     8,
    "N/A":       0,
}

# Claim types that carry hard factual weight — penalised at 2× normal weight
HIGH_RISK_TYPES = {"FACTUAL_DATE", "FACTUAL_NUMBER", "FACTUAL_NAME", "QUOTE"}

# Words that indicate epistemic humility — low ratio on long responses is a red flag
HEDGE_WORDS = {
    "might", "may", "could", "possibly", "approximately", "around",
    "some", "often", "generally", "typically", "suggest", "indicate",
    "appear", "seem", "likely", "unlikely", "perhaps", "allegedly",
}

# ─── Pre-flight heuristics (zero LLM cost) ───────────────────────────────────

def _entity_density(text: str) -> float:
    """
    Rough ratio of high-risk tokens (capitalised words, numbers, years) to
    total words. Responses above ~0.15 are claim-heavy and warrant extra scrutiny.
    """
    words = text.split()
    if not words:
        return 0.0
    risky = sum(
        1 for w in words
        if re.match(r"\b[A-Z][a-z]{2,}\b", w)   # capitalised proper-noun-like
        or re.match(r"\b\d{4}\b", w)              # 4-digit year
        or re.match(r"\b\d+\.?\d*\b", w)          # any number
    )
    return risky / len(words)


def _hedge_ratio(text: str) -> float:
    """
    Ratio of hedging words to total words. A long factual response with
    hedge_ratio < 0.01 is asserting everything as certain — a red flag.
    """
    words = text.lower().split()
    return sum(1 for w in words if w in HEDGE_WORDS) / max(1, len(words))


def _pre_flight_flags(response: str) -> dict:
    """Return lightweight heuristic flags logged alongside trust details."""
    density = _entity_density(response)
    hedge = _hedge_ratio(response)
    return {
        "entity_density": round(density, 3),
        "hedge_ratio": round(hedge, 3),
        "high_entity_density": density > 0.15,
        "low_hedge_on_long_response": hedge < 0.01 and len(response.split()) > 80,
    }

# ─── JSON helpers ────────────────────────────────────────────────────────────

def _extract_json(raw: str):
    """
    Try strict parse first, fall back to extracting the first {...} block.
    Handles models that prepend/append prose or wrap in markdown fences.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    try:
        return json.loads(raw)
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None

# ─── Scoring ─────────────────────────────────────────────────────────────────

def _derive_score(details: dict) -> int:
    """
    Weighted penalty scoring:
      - HIGH_RISK_TYPES (dates, numbers, names, quotes) count 2× in the denominator.
      - CONTRADICTED verdicts carry a 1.5× multiplier on top of severity penalty.
      - Internal consistency failures (self_contradiction, causal_chain_risk) add
        flat bonuses to the penalty pool.
    """
    claims = details.get("claims", []) if isinstance(details, dict) else []
    if not isinstance(claims, list) or not claims:
        return DEFAULT_TRUST_SCORE

    total_weight = 0.0
    total_penalty = 0.0

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        verdict    = str(claim.get("verdict",    "")).upper()
        severity   = str(claim.get("severity",   "MINOR")).upper()
        claim_type = str(claim.get("claim_type", "OTHER")).upper()

        # High-risk claim types count double in the weight pool
        weight = 2.0 if claim_type in HIGH_RISK_TYPES else 1.0
        total_weight += weight

        if verdict in ("UNSUPPORTED", "CONTRADICTED"):
            base = SEVERITY_PENALTY.get(severity, 20)
            # Contradicted is actively wrong, not just unverified — 1.5× multiplier
            multiplier = 1.5 if verdict == "CONTRADICTED" else 1.0
            total_penalty += weight * base * multiplier

    # Flat penalties for structural failure modes detected in Stage 4
    consistency = details.get("consistency", {})
    if consistency.get("self_contradiction"):
        total_penalty += 25
    if consistency.get("causal_chain_risk"):
        total_penalty += 10

    if total_weight == 0:
        return DEFAULT_TRUST_SCORE

    raw_score = 100.0 - (total_penalty / total_weight)
    return max(0, min(100, int(round(raw_score))))


def _ensure_summary(details: dict) -> dict:
    """
    Recompute the summary block from the claims list, overwriting whatever
    the LLM returned to prevent it from inflating its own scores.
    Now supports 4-tier hallucination_risk: LOW / MEDIUM / HIGH / CRITICAL.
    """
    if not isinstance(details, dict):
        return details

    claims = details.get("claims", [])
    if not isinstance(claims, list):
        claims = []

    supported = unsupported = contradicted = not_applicable = critical_count = 0
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        verdict  = str(claim.get("verdict",  "")).upper()
        severity = str(claim.get("severity", "")).upper()
        if verdict == "SUPPORTED":
            supported += 1
        elif verdict == "UNSUPPORTED":
            unsupported += 1
        elif verdict == "CONTRADICTED":
            contradicted += 1
        elif verdict == "NOT_APPLICABLE":
            not_applicable += 1
        if severity == "CRITICAL" and verdict in ("UNSUPPORTED", "CONTRADICTED"):
            critical_count += 1

    total = max(1, len(claims))
    unsupported_ratio = (unsupported + contradicted) / total
    consistency = details.get("consistency", {})
    has_self_contradiction = contradicted > 0 or consistency.get("self_contradiction", False)

    if critical_count >= 2 or (contradicted > 0 and unsupported_ratio > 0.4):
        risk = "CRITICAL"
    elif has_self_contradiction or unsupported_ratio > 0.3:
        risk = "HIGH"
    elif unsupported_ratio > 0.1:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    details["summary"] = {
        "supported":          supported,
        "unsupported":        unsupported,
        "contradicted":       contradicted,
        "not_applicable":     not_applicable,
        "critical_count":     critical_count,
        "hallucination_risk": risk,
    }
    return details

# ─── Main async evaluator ────────────────────────────────────────────────────

async def evaluate_trust(query_id: str, prompt: str, response: str, context: str = ""):
    """
    Background task: call Gemini Flash to audit the response for hallucinations,
    then update the query_logs row with a trust_score (0–100) and trust_details JSON.
    Completely fail-silent — never raises to the caller.
    """
    raw = None
    try:
        # ── Pre-flight heuristics (no LLM cost) ──────────────────────────────
        preflight = _pre_flight_flags(response)

        # ── LLM evaluation ────────────────────────────────────────────────────
        result = await _openai.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": TRUST_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": TRUST_USER_PROMPT.format(
                        prompt=prompt[:1000],
                        response=response[:3000],
                        context=context[:1500],
                    ),
                },
            ],
            temperature=0,
            max_tokens=900,
        )

        raw = result.choices[0].message.content.strip()
        details = _extract_json(raw) or {}

        # Always recompute summary from raw claims — never trust the LLM's own tally
        details = _ensure_summary(details)
        details["preflight"] = preflight

        score = _derive_score(details)

        # ── Persist to Supabase ───────────────────────────────────────────────
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
            # Fallback: at minimum, persist the score even if JSONB column fails
            if "trust_details" in payload:
                supabase.table("query_logs").update({"trust_score": score}).eq(
                    "id", query_id
                ).execute()

    except Exception as e:
        print(
            f"TRUST EVAL ERROR: {e}\n"
            f"RAW REASON: {repr(raw) if raw is not None else 'None'}",
            file=sys.stderr,
        )
