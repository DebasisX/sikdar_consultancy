"""Input validation helpers for Indian identifiers."""
from __future__ import annotations

import re

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def normalize_pan(v: str) -> str:
    return re.sub(r"\s+", "", v or "").upper()


def valid_pan(v: str) -> bool:
    return bool(PAN_RE.match(normalize_pan(v)))


def normalize_aadhar(v: str) -> str:
    return re.sub(r"\D", "", v or "")


def valid_aadhar(v: str) -> bool:
    d = normalize_aadhar(v)
    return len(d) == 12 and d[0] in "23456789"


def format_aadhar(v: str) -> str:
    d = normalize_aadhar(v)
    return " ".join(d[i:i + 4] for i in range(0, len(d), 4)) if d else ""


def mask_aadhar(v: str) -> str:
    d = normalize_aadhar(v)
    return f"XXXX XXXX {d[-4:]}" if len(d) == 12 else (v or "")


def normalize_phone(v: str) -> str:
    d = re.sub(r"\D", "", v or "")
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d


def valid_phone(v: str) -> bool:
    d = normalize_phone(v)
    return len(d) == 10 and d[0] in "6789"


def format_phone(v: str) -> str:
    d = normalize_phone(v)
    return f"+91 {d[:5]} {d[5:]}" if len(d) == 10 else (v or "")


def valid_email(v: str) -> bool:
    return bool(EMAIL_RE.match((v or "").strip()))


def inr(amount: float) -> str:
    """Format a number in the Indian digit grouping, e.g. ₹12,34,567."""
    neg = amount < 0
    amount = abs(amount)
    whole = int(amount)
    paise = round((amount - whole) * 100)
    if paise == 100:
        whole, paise = whole + 1, 0
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    out = "₹" + s + (f".{paise:02d}" if paise else "")
    return "-" + out if neg else out
