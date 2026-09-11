"""Document type classification (Team B)."""

from __future__ import annotations

from typing import Any

# Canonical document types used by the demo / sample-data.
DOCUMENT_TYPES = ("kyc", "bank_statement", "dealer_invoice", "platform_earnings")

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "kyc": ("kyc", "aadhaar", "pan", "passport", "identity", "address proof", "dob"),
    "bank_statement": ("bank statement", "account statement", "credits", "debits", "ifsc", "bank"),
    "dealer_invoice": ("invoice", "dealer", "vehicle price", "chassis", "ex-showroom", "on-road price"),
    "platform_earnings": ("platform", "gig", "swiggy", "zomato", "uber", "ola", "rapido", "earnings", "payout"),
}

EXPECTED: dict[str, list[str]] = {
    "kyc": ["full_name", "identity", "address"],
    "bank_statement": ["monthly_income", "bank_credits", "existing_monthly_obligations", "address"],
    "dealer_invoice": ["vehicle_price", "loan_amount"],
    "platform_earnings": ["platform_income", "employment_income", "monthly_income"],
}


def classify_document(filename: str, text_preview: str = "") -> str:
    """Keyword-based classification (deterministic, zero-cost)."""
    hay = f"{filename or ''} {text_preview or ''}".lower()
    best, best_hits = "kyc", 0
    for dtype, keys in _KEYWORDS.items():
        hits = sum(1 for k in keys if k in hay)
        if hits > best_hits:
            best, best_hits = dtype, hits
    # filename hints win ties
    low = (filename or "").lower()
    if "bank" in low:
        return "bank_statement"
    if "invoice" in low or "dealer" in low:
        return "dealer_invoice"
    if "platform" in low or "earning" in low:
        return "platform_earnings"
    if "kyc" in low:
        return "kyc"
    return best


def expected_fields(doc_type: str) -> list[str]:
    """Return the expected evidence fields for a document type."""
    return list(EXPECTED.get(doc_type, ["monthly_income"]))