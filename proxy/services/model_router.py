import re
from typing import Tuple

# ─── Cost table: $/million tokens (input, output) ────────────
MODEL_COSTS: dict[str, Tuple[float, float]] = {
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant":    (0.05, 0.08),
    "sarvam-1":        (0.10,   0.10),
    # legacy for compatibility
    "grok-2":          (5.00,  15.00),
    "grok-2-mini":     (0.15,   0.60),
    "gpt-4o":          (5.00,  15.00),
}

# ─── Premium → cheap model mapping ───────────────────────────
_DOWNGRADE_MAP: dict[str, str] = {
    "llama-3.3-70b-versatile": "llama-3.1-8b-instant",
    "grok-2": "llama-3.1-8b-instant",
    "gpt-4o": "llama-3.1-8b-instant",
}

# ─── Sarvam specific Indian context patterns ─────────────────
_SARVAM_PATTERNS = [
    r"\b[\u0900-\u097F]+\b",  # matches Hindi/Devanagari script
    r"\bbengaluru\b",
    r"\bindia\b",
    r"\bupi\b",
    r"\brupees?\b",
    r"\bcmrit\b",
    r"\bflipkart\b",
    r"\bzomato\b",
    r"\bswiggy\b",
    r"\bhindi\b",
]
_sarvam_compiled = [re.compile(p, re.IGNORECASE) for p in _SARVAM_PATTERNS]

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
    r"\bexplain (about|the|how|why|what)\b",
    r"\btell me about\b",
    r"\bwho (is|was|were)\b",
    r"\bwhat (is|are|was|were)\b",
    r"\bwhen (did|was|is)\b",
    r"\bwhere (is|was|did)\b",
    r"\bhow (does|do|did|is|are)\b",
    r"\bdescribe (the|a|an)\b",
    r"\bgive me (a |an )?(brief|short|quick|simple)\b",
    r"\bwhat happened\b",
    r"\bhistory of\b",
    r"\bwhat (do you know|can you tell)\b",
]
_compiled = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_PATTERNS]
_SHORT_PROMPT_WORDS = 15  # only extremely short prompts default to simple

_COMPLEX_PATTERNS = [
    r"\bpython\b",
    r"\bscript\b",
    r"\bcode\b",
    r"\bdatabase\b",
    r"\bmulti-threaded\b",
    r"\basyncio\b",
    r"\bwrite.*extremely.*detailed\b",
    r"\bwrite.*comprehensive\b",
    r"\bwrite.*in-depth\b",
    r"\bdetailed.*analysis\b",
    r"\bresearch (paper|report|essay)\b",
    r"\bthorough\b",
    r"\bexhaustive\b",
    r"\bstep[- ]by[- ]step.*implementation\b",
    r"\barchitecture\b",
    r"\bdesign (a |the )?system\b",
    r"\bwikipedia\b",
]
_compiled_complex = [re.compile(p, re.IGNORECASE) for p in _COMPLEX_PATTERNS]

def is_simple_prompt(text: str) -> bool:
    """Heuristic: is this prompt safe to route to a cheaper model?"""
    if any(p.search(text) for p in _compiled_complex):
        return False
        
    if len(text.split()) <= _SHORT_PROMPT_WORDS:
        return True
    return any(p.search(text) for p in _compiled)

def is_sarvam_prompt(text: str) -> bool:
    """Heuristic: does this prompt contain Indian context optimized for Sarvam?"""
    return any(p.search(text) for p in _sarvam_compiled)

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
    """
    if is_sarvam_prompt(prompt):
        return "sarvam-1", 0.0
        
    for premium, cheap in _DOWNGRADE_MAP.items():
        if premium in requested and is_simple_prompt(prompt):
            saved = _estimate_saved(premium, cheap)
            return cheap, saved
    return requested, 0.0
