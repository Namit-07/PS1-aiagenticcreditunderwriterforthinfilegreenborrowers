"""Deterministic field extraction from borrower documents (Team B).

Deterministic in MOCK_AI_MODE: parses text with label-anchored regexes for
income / loan / price / obligations / identity / name. The LLM path (non-mock) only
re-labels confidence; numeric values are still parsed here and never trusted blindly.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def extract_pdf_text(path: str | Path) -> list[dict[str, Any]]:
    """Extract per-page text from a PDF ({page, text})."""
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF (fitz) is required for PDF parsing") from exc
    doc = fitz.open(str(path))
    out: list[dict[str, Any]] = []
    for i, page in enumerate(doc):
        try:
            text = page.get_text("text") or ""
        except Exception:
            text = ""
        out.append({"page": i + 1, "text": text})
    try:
        doc.close()
    except Exception:
        pass
    return out


def pdf_metadata(path: str | Path) -> dict[str, Any]:
    """Return basic PDF metadata (page count, best-effort)."""
    try:
        import fitz

        doc = fitz.open(str(path))
        meta = {"pages": doc.page_count}
        try:
            doc.close()
        except Exception:
            pass
        return meta
    except Exception:
        return {"pages": 0}


_MONEY = re.compile(r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)
_PLAIN_NUM = re.compile(r"\b(\d{4,7})\b")
_ANY_MONEY = re.compile(
    r"(?:rs\.?|inr|₹)?\s*([\d]{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d{4,8}(?:\.\d+)?)", re.IGNORECASE
)
_DAMAGED = re.compile(r"[?#*]{1,}|illegible|unreadable|smudged|\[low quality", re.IGNORECASE)

# Label-anchored patterns: the FIRST money value on the same line as the label wins.
# Ordered from most to least specific so the specific label is preferred.
_LABELS: dict[str, list[str]] = {
    "monthly_income": [
        r"(?:average|avg\.?|net|gross|verified|declared)\s+monthly\s+(?:income|salary|earnings?|payout)",
        r"monthly\s+(?:income|salary|earnings?|payout)",
        r"declared\s+income",
        r"salary\s+credit(?:ed)?",
        r"\bincome\b",
    ],
    "loan_amount": [
        r"loan\s+(?:amount|requested|required|sanctioned|applied)",
        r"finance\s+amount",
        r"\bloan\b",
    ],
    "vehicle_price": [
        r"(?:on[- ]road|ex[- ]showroom|vehicle|invoice|total|grand\s+total)\s+(?:price|value|amount)",
        r"\bprice\b",
    ],
    "existing_monthly_obligations": [
        r"(?:existing|current|total)\s+(?:monthly\s+)?(?:emi|obligations?|loan\s+repayments?)",
        r"\bemi\b",
        r"obligation",
    ],
    "platform_income": [
        r"(?:total|net|average|monthly)\s+(?:platform\s+)?(?:payout|earnings?)",
        r"\bpayout\b",
        r"\bearnings?\b",
    ],
    "employment_income": [r"(?:salary|wages?|employment\s+income)"],
    "bank_credits": [r"monthly\s+credits?(?:\s*\(last\s+\d+\s+months?\))?", r"credits?\s+history"],
}
_NUMERIC_FIELDS = set(_LABELS)
_TEXT_LABELS: dict[str, str] = {
    "full_name": (
        r"(?:account\s+holder\s+|customer\s+|applicant\s+|buyer\s+|partner\s+)?name\s*[:\-]\s*"
        r"([A-Za-z][A-Za-z .]{2,60})"
    ),
    "identity": (
        r"(?:aadhaar|pan|passport|voter\s*id|id)\s*(?:no\.?|number|#)?\s*[:\-]\s*"
        r"([A-Za-z0-9Xx][A-Za-z0-9Xx\- ]{4,24})"
    ),
    "address": r"address\s*[:\-]\s*([^\n]{6,120})",
}


def _first_money(text: str) -> float | None:
    m = _MONEY.search(text or "")
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _all_money(text: str) -> list[float]:
    out: list[float] = []
    for m in _ANY_MONEY.finditer(text or ""):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return out


def _labelled_line(field: str, text: str) -> tuple[str, int] | None:
    """Return (line, label_rank) of the first line carrying a label for ``field``."""
    for rank, pattern in enumerate(_LABELS.get(field, [])):
        rx = re.compile(pattern, re.IGNORECASE)
        for line in (text or "").splitlines():
            if rx.search(line):
                return line, rank
    return None


def _field_from_text(
    field: str, text: str, source: str, page: int | None = 1
) -> dict[str, Any] | None:
    """Deterministic, label-anchored field extraction.

    Confidence heuristic (deterministic, no LLM):
      * value found on a line with a specific label   -> 0.92
      * value found on a line with a generic keyword  -> 0.75
      * bare large number fallback                    -> 0.55
      * line looks damaged (?, #, 'illegible', ...)   -> capped at 0.40
    """
    low = (text or "").lower()
    val: Any = None
    conf = 0.5
    snippet = (text or "")[:280]

    if field in _TEXT_LABELS:
        m = re.search(_TEXT_LABELS[field], text or "", re.IGNORECASE)
        if m:
            val = m.group(1).strip().rstrip(".")
            conf = 0.9 if field == "identity" else 0.85
            snippet = m.group(0)[:280]
            if _DAMAGED.search(m.group(0)):
                conf = min(conf, 0.40)
    elif field in _NUMERIC_FIELDS:
        hit = _labelled_line(field, text)
        if hit:
            line, rank = hit
            after = line.split(":", 1)[1] if ":" in line else line
            if field == "bank_credits":
                nums = _all_money(after)
                if len(nums) >= 2:
                    val = nums
                    conf = 0.9
            else:
                val = _first_money(after)
                if val is None:
                    nums = _all_money(after)
                    val = nums[0] if nums else None
                if val is not None:
                    conf = 0.92 if rank == 0 else 0.75
            snippet = line.strip()[:280]
            if val is not None and _DAMAGED.search(line):
                conf = min(conf, 0.40)
        if val is None and field in {"monthly_income", "loan_amount", "vehicle_price"}:
            m2 = _PLAIN_NUM.search(text or "")
            if m2:
                try:
                    val = float(m2.group(1))
                    conf = 0.55
                except ValueError:
                    val = None
    if val is None:
        return None
    if _DAMAGED.search(low[:2000]) and conf > 0.6 and field in {"monthly_income", "identity"}:
        # whole-document quality warning lowers trust in the critical fields
        conf = min(conf, 0.58)
    return {
        "field": field,
        "value": val,
        "source_document": source,
        "page": page,
        "confidence": round(conf, 3),
        "evidence": snippet,
    }
