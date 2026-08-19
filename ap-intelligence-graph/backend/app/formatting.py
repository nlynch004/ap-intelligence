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
_MONTH_NAME_TO_NUM = {name.lower(): num for num, name in MONTH_NAMES.items()}
_MONTH_MENTION_RE = re.compile(r"\b(" + "|".join(MONTH_NAMES.values()) + r")\s+(\d{4})\b", re.IGNORECASE)
_PLANNING_PERIOD_RE = re.compile(r"\b([Qq][1-4]|[Hh][12])\b(?:\s+(\d{4}))?")


def format_month(month: str) -> str:
    """'2026-05' -> 'May 2026'. Falls back to the raw string if unparsable."""
    year, _, mon = month.partition("-")
    name = MONTH_NAMES.get(mon)
    return f"{name} {year}" if name else month


def parse_month_mention(text: str) -> str | None:
    """Reverse of format_month: finds the first 'May 2026'-style mention in
    free text and returns '2026-05'. Deterministic - used to resolve which
    campaign a chat message like "Review Summit Sisters' May 2026 campaign"
    refers to, never left to the LLM to guess."""
    match = _MONTH_MENTION_RE.search(text)
    if not match:
        return None
    name, year = match.groups()
    num = _MONTH_NAME_TO_NUM.get(name.lower())
    return f"{year}-{num}" if num else None


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


def extract_planning_period(text: str) -> str | None:
    """Finds a 'Q4'/'H1'-style planning-period mention (optionally with a
    year, e.g. 'Q4 2026') in free text. Deterministic - used to resolve
    Plan.planning_period from a bounded chat request like "Build Northwind's
    Q4 creator plan," never left to the LLM to invent (spec Phase 6 Sec.10:
    "Build Northwind's next creator plan" is also valid with no period at
    all - this returns None in that case rather than guessing one)."""
    match = _PLANNING_PERIOD_RE.search(text)
    if not match:
        return None
    period, year = match.groups()
    period = period[0].upper() + period[1]
    return f"{period} {year}" if year else period
