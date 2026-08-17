"""Small, dependency-free deterministic formatting/parsing helpers shared
across routers and the memory layer. Nothing here talks to the database or
the LLM - it exists purely so the same logic (month labels, dollar-amount
parsing) isn't duplicated in multiple places (previously: graph.py had its
own month-name table, and llm/mock_provider.py had its own dollar-amount
regex - both now live here once).
"""

import re

MONTH_NAMES = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}

_DOLLAR_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*(k\b)?", re.IGNORECASE)


def format_month(month: str) -> str:
    """'2026-05' -> 'May 2026'. Falls back to the raw string if unparsable."""
    year, _, mon = month.partition("-")
    name = MONTH_NAMES.get(mon)
    return f"{name} {year}" if name else month


def extract_dollar_amount(text: str) -> float | None:
    """Finds the first '$<amount>' (optionally '$6k') in free text.
    Deterministic - used for the "commercial ask" evidence figure, never
    left to the LLM to compute (spec Step 5 Sec.1)."""
    match = _DOLLAR_RE.search(text)
    if not match:
        return None
    raw, k = match.groups()
    value = float(raw.replace(",", ""))
    if k:
        value *= 1000
    return value
