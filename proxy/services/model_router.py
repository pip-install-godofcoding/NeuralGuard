import re
from typing import Tuple

# ─── Cost table: $/million tokens (input, output) ────────────
MODEL_COSTS: dict[str, Tuple[float, float]] = {
    "gemini-2.5-pro":  (1.25, 5.00),
    "gemini-2.5-flash": (0.075, 0.30),
    "gpt-4o":          (5.00,  15.00),
    "gpt-4o-mini":     (0.15,   0.60),
    "gpt-4":           (30.00, 60.00),
    "gpt-3.5-turbo":   (0.50,   1.50),
}

# ─── Premium → cheap model mapping ───────────────────────────
_DOWNGRADE_MAP: dict[str, str] = {
    "gemini-2.5-pro": "gemini-2.5-flash",
    "gpt-4o": "gpt-4o-mini",
    "gpt-4":  "gpt-3.5-turbo",
}

# ─── Simple-task patterns ─────────────────────────────────────
_SIMPLE_PATTERNS = [
    r"\btranslate\b",
    r"\bsummariz(e|ing|ation)\b",
    r"\bin one sentence\b",
    r"\bfix (the )?(grammar|spelling|typos?)\b",
    r"\bcorrect (the )?(grammar|spelling)\b",
    r"\blist the\b",
    r"\bwhat is \w+\??$",
    r"\bdefine \w+",
    r"\bconvert\b",
    r"\bparaphrase\b",
    r"\bexpand (this|the)\b",
    r"\bformat (this|the)\b",
    r"\bclassify\b",
    r"\bextract\b",
    r"\brephrase\b",
]
_compiled = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_PATTERNS]
_SHORT_PROMPT_WORDS = 15  # only extremely short prompts default to simple

_COMPLEX_PATTERNS = [r"\bpython\b", r"\bscript\b", r"\bcode\b", r"\bdatabase\b", r"\bmulti-threaded\b", r"\basyncio\b"]
_compiled_complex = [re.compile(p, re.IGNORECASE) for p in _COMPLEX_PATTERNS]

def is_simple_prompt(text: str) -> bool:
    """Heuristic: is this prompt safe to route to a cheaper model?"""
    # Never downgrade if it's explicitly asking for complex code
    if any(p.search(text) for p in _compiled_complex):
        return False
        
    if len(text.split()) <= _SHORT_PROMPT_WORDS:
        return True
    return any(p.search(text) for p in _compiled)


def estimate_cost(model: str, usage: dict) -> float:
    """Estimate actual cost in USD from token usage."""
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    for key, (inp, out) in MODEL_COSTS.items():
        if key in model:
            return (prompt_tokens * inp + completion_tokens * out) / 1_000_000
    return 0.0


def _estimate_saved(premium: str, cheap: str, avg_tokens: int = 500) -> float:
    """Estimate cost delta between premium and cheap model (rough)."""
    p_in, p_out = MODEL_COSTS.get(premium, (0.0, 0.0))
    c_in, c_out = MODEL_COSTS.get(cheap, (0.0, 0.0))
    tok_m = avg_tokens / 1_000_000
    return max(0.0, ((p_in + p_out) - (c_in + c_out)) * tok_m)


def route_model(requested: str, prompt: str) -> Tuple[str, float]:
    """
    Returns (model_to_use, estimated_cost_saved_usd).
    Silently downgrades premium models for simple prompts.
    Always fails open — returns (requested, 0.0) if no rule matches.
    """
    for premium, cheap in _DOWNGRADE_MAP.items():
        if premium in requested and is_simple_prompt(prompt):
            saved = _estimate_saved(premium, cheap)
            return cheap, saved
    return requested, 0.0
