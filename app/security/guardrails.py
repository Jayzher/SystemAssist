import re


BLOCKED_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|rules|prompts)",
    r"disregard\s+(all\s+)?(previous|above|prior)",
    r"you\s+are\s+now\s+",
    r"pretend\s+you\s+are",
    r"act\s+as\s+(if\s+)?(you\s+)?(are\s+|were\s+)?",
    r"override\s+(system|safety|security)",
    r"reveal\s+(your|the)\s+(system|internal|hidden)\s+(prompt|instructions|rules)",
    r"show\s+me\s+(the\s+)?(source|backend|api|code|schema|database)",
    r"what\s+(is|are)\s+(your|the)\s+(system\s+)?(prompt|instructions|rules)",
    r"dump\s+(all|the)\s+(data|logs|users)",
    r"sql\s+injection|drop\s+table|delete\s+from",
    r"exec\s*\(|eval\s*\(|__import__",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


def detect_prompt_injection(query: str) -> bool:
    for pattern in COMPILED_PATTERNS:
        if pattern.search(query):
            return True
    return False


def sanitize_query(query: str) -> str:
    cleaned = query.strip()
    cleaned = re.sub(r"[<>{}|\\`]", "", cleaned)
    if len(cleaned) > 2000:
        cleaned = cleaned[:2000]
    return cleaned


def validate_ai_response(response: str) -> str:
    sensitive_patterns = [
        r"mongodb(\+srv)?://[^\s]+",
        r"password\s*[:=]\s*[^\s]+",
        r"secret\s*[:=]\s*[^\s]+",
        r"api[_-]?key\s*[:=]\s*[^\s]+",
        r"token\s*[:=]\s*[A-Za-z0-9._-]{20,}",
    ]
    cleaned = response
    for pattern in sensitive_patterns:
        cleaned = re.sub(pattern, "[REDACTED]", cleaned, flags=re.IGNORECASE)
    return cleaned
