import re

# ---------------------------------------------------------------------------
# Input guardrails
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?|context)",
    r"forget\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?|context)",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)",
    r"you\s+are\s+now\s+(a\s+)?(?!an?\s+assistant)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(a\s+)?(different|new|another|unrestricted)",
    r"(jailbreak|developer\s+mode|dan\s+mode)",
    r"override\s+(your\s+)?(instructions?|rules?|system)",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions?|rules?)",
    r"new\s+system\s+prompt",
]

_OFF_TOPIC_PATTERNS = [
    r"\bwrite\s+(me\s+)?(a\s+)?(poem|song|story|essay|joke|novel)\b",
    r"\b(weather|forecast|temperature)\b",
    r"\b(recipe|cook|bake|ingredient)\b",
    r"\b(movie|music|sport|game|celebrity)\b",
    r"\btranslate\s+(this|the|to)\b",
    # geography / general knowledge — handle both "what is" and "what's"
    r"\bwhat'?s?\s+(is\s+)?the\s+capital\s+of\b",
    r"\b(capital\s+city|largest\s+city|population\s+of)\b",
    r"\b(country|continent|geography|history\s+of)\b",
]


def check_input(question: str) -> tuple[bool, str]:
    """
    Validate user input before sending to the LLM.

    Returns:
        (True, "")           — input is safe to process
        (False, reason)      — input rejected; reason is shown to the user
    """
    if len(question.strip()) < 5:
        return False, "Please enter a complete question."

    q = question.lower()

    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, q):
            return False, "Your question contains content that cannot be processed. Please ask about company documents."

    for pattern in _OFF_TOPIC_PATTERNS:
        if re.search(pattern, q):
            return False, "I can only answer questions about company documents such as HR policies, billing records, or employee information."

    return True, ""


# ---------------------------------------------------------------------------
# Output guardrails
# ---------------------------------------------------------------------------

_REDIRECT_MESSAGE = (
    "I can only answer questions about company documents. "
    "Please ask about HR policies, billing records, or employee information."
)


def is_irrelevant_response(answer: str) -> bool:
    """Return True if the LLM produced no real answer — empty or sources only."""
    if not answer.strip():
        return True
    sources_index = answer.find("Sources:")
    content = answer[:sources_index].strip() if sources_index != -1 else answer.strip()
    return not content


def check_output(answer: str) -> list[str]:
    """
    Validate LLM output and return a list of warning strings.
    Warnings are logged but the answer is NOT modified here —
    prompt guardrails are the primary fix; this is a detection layer.
    """
    warnings = []

    urls = re.findall(r"https?://\S+", answer)
    if urls:
        warnings.append(f"GUARDRAIL: Response contains {len(urls)} generated URL(s) — prompt guardrail may need strengthening.")

    if "Sources:" not in answer:
        warnings.append("GUARDRAIL: Response is missing the Sources section.")

    return warnings
