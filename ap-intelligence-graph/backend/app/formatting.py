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
    year, _, mon = month.partition("-")
    name = MONTH_NAMES.get(mon)
    return f"{name} {year}" if name else month


def parse_month_mention(text: str) -> str | None:
    match = _MONTH_MENTION_RE.search(text)
    if not match:
        return None
    name, year = match.groups()
    num = _MONTH_NAME_TO_NUM.get(name.lower())
    return f"{year}-{num}" if num else None


def extract_dollar_amount(text: str) -> float | None:
    match = _DOLLAR_RE.search(text)
    if not match:
        return None
    raw, k = match.groups()
    value = float(raw.replace(",", ""))
    if k:
        value *= 1000
    return value


def extract_planning_period(text: str) -> str | None:
    match = _PLANNING_PERIOD_RE.search(text)
    if not match:
        return None
    period, year = match.groups()
    period = period[0].upper() + period[1]
    return f"{period} {year}" if year else period
