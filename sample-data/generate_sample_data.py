"""Generate SYNTHETIC borrower documents + scenario fixtures (no real PII).

Run from the repo root:

    python sample-data/generate_sample_data.py

Writes
  sample-data/borrower-00N/*.txt        plain-text "documents" (kyc, bank statement,
                                        dealer invoice, platform earnings)
  test-cases/<scenario>.json            application payload + documents + expected outcome,
                                        consumed by ai-service/tests and backend/tests
  test-cases/README.md                  scenario matrix

Every number is invented. Names are placeholders. Deterministic output (no randomness).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample-data"
CASES = ROOT / "test-cases"


# --------------------------------------------------------------------------- #
# document templates (label-anchored so the deterministic extractor can read them)
# --------------------------------------------------------------------------- #
def kyc(name: str, aadhaar_tail: str, dob: str, address: str, damaged: bool = False) -> str:
    id_line = f"Aadhaar No: XXXX-XXXX-{aadhaar_tail}"
    return (
        "KYC DOCUMENT - Aadhaar (SYNTHETIC, for demo only)\n"
        f"Name: {name}\n"
        f"{id_line}\n"
        f"DOB: {dob}\n"
        f"Address: {address}\n"
        + ("[low quality scan] parts of this page are illegible\n" if damaged else "")
    )


def bank_statement(name: str, credits: list[int], avg_income: int, emi: int, damaged: bool = False,
                   address: str | None = None) -> str:
    credits_line = " ; ".join(f"Rs {c:,}" for c in credits)
    income_line = (
        f"Average monthly income (credits): Rs {str(avg_income)[0]}?,{str(avg_income)[-3:]} [low quality scan]"
        if damaged
        else f"Average monthly income (credits): Rs {avg_income:,}"
    )
    body = (
        "BANK STATEMENT - Demo Bank Ltd (SYNTHETIC)\n"
        f"Account holder name: {name}\n"
        + (f"Address: {address}\n" if address else "")
        + "IFSC: DEMO0001234   Account: XXXXXX7788\n"
        "Statement period: last 6 months\n"
    )
    if not damaged:
        body += f"Monthly credits (last 6 months): {credits_line}\n"
    body += income_line + "\n"
    body += f"Existing EMI obligations: Rs {emi:,}\n"
    body += "Closing balance trend: stable\n"
    return body


def dealer_invoice(name: str, vehicle: str, price: int, loan: int) -> str:
    return (
        "DEALER INVOICE - GreenWheels EV Pvt Ltd (SYNTHETIC)\n"
        f"Buyer name: {name}\n"
        f"Vehicle: {vehicle}\n"
        f"On-road price: Rs {price:,}\n"
        f"Loan amount requested: Rs {loan:,}\n"
        "Chassis: SYN-0000-DEMO\n"
    )


def platform_earnings(name: str, monthly_payout: int, months: int = 6) -> str:
    return (
        "PLATFORM EARNINGS - GigApp partner payout summary (SYNTHETIC)\n"
        f"Partner name: {name}\n"
        f"Average monthly payout: Rs {monthly_payout:,}\n"
        f"Total earnings ({months} months): Rs {monthly_payout * months:,}\n"
        "Active days per month: 24\n"
    )


# --------------------------------------------------------------------------- #
# borrowers
# --------------------------------------------------------------------------- #
BORROWERS = {
    "borrower-001": {
        "name": "Ravi Kumar", "tail": "4321", "dob": "12/03/1996", "address": "14 MG Road, Pune 411001",
        "credits": [38500, 41000, 36200, 39800, 37900, 40100], "avg_income": 38900, "emi": 2500,
        "vehicle": "EV scooter (2 wheeler)", "price": 120000, "loan": 90000, "payout": 39000,
        "age": 29, "declared": 39000, "tenure": 36, "rate": 14.0,
    },
    "borrower-002": {
        "name": "Priya Sharma", "tail": "8765", "dob": "05/09/1994", "address": "22 Lake View, Bengaluru 560001",
        "credits": [38500, 37200, 39900, 38100, 36800, 40500], "avg_income": 38500, "emi": 3000,
        "vehicle": "EV auto rickshaw (3 wheeler)", "price": 240000, "loan": 180000, "payout": 38000,
        "age": 31, "declared": 45000, "tenure": 48, "rate": 15.0,
    },
    "borrower-003": {
        "name": "Arjun Mehta", "tail": "1122", "dob": "20/01/1999", "address": "7 Station Road, Jaipur 302001",
        "credits": [22000, 21500, 23800, 20900, 22600, 21200], "avg_income": 22000, "emi": 6000,
        "vehicle": "EV scooter (2 wheeler, premium)", "price": 200000, "loan": 150000, "payout": 22000,
        "age": 26, "declared": 22000, "tenure": 24, "rate": 16.0,
    },
}


def write_docs(key: str, b: dict, damaged_bank: bool = False, name_on_kyc: str | None = None,
               skip: tuple[str, ...] = ()) -> list[dict]:
    d = SAMPLE / key
    d.mkdir(parents=True, exist_ok=True)
    name = b["name"]
    files = {
        "kyc.txt": kyc(name_on_kyc or name, b["tail"], b["dob"], b["address"]),
        "bank_statement.txt": bank_statement(name, b["credits"], b["avg_income"], b["emi"], damaged_bank,
                                             address=b["address"]),
        "dealer_invoice.txt": dealer_invoice(name, b["vehicle"], b["price"], b["loan"]),
        "platform_earnings.txt": platform_earnings(name, b["payout"]),
    }
    kinds = {"kyc.txt": "kyc", "bank_statement.txt": "bank_statement",
             "dealer_invoice.txt": "dealer_invoice", "platform_earnings.txt": "platform_earnings"}
    docs = []
    for fname, text in files.items():
        if kinds[fname] in skip:
            continue
        # canonical borrower folders always hold the clean documents
        if not damaged_bank and not name_on_kyc and not skip:
            (d / fname).write_text(text, encoding="utf-8")
        doc = {"document_id": f"{key}/{fname}", "filename": fname, "kind": kinds[fname], "text": text}
        if damaged_bank and fname == "bank_statement.txt":
            doc["ocr_confidence"] = 0.5
        docs.append(doc)
    return docs


def application(app_id: str, b: dict, **over) -> dict:
    loan = over.get("loan", b["loan"])
    price = over.get("price", b["price"])
    tenure = over.get("tenure", b["tenure"])
    return {
        "id": app_id,
        "status": "underwriting",
        "product": {"type": over.get("product", "ev_two_wheeler"), "amount": loan,
                    "tenure_months": tenure, "rate_annual": over.get("rate", b["rate"])},
        "borrower": {"ref_id": f"REF-{app_id}", "age": over.get("age", b["age"]),
                     "location_tier": over.get("tier", "tier_2"), "full_name": b["name"],
                     "declared_monthly_income": over.get("declared", b["declared"]),
                     "employment_type": "gig_platform"},
        "loan_request": {"amount": loan, "tenure_months": tenure, "vehicle_price": price,
                         "down_payment": max(0, price - loan)},
    }


def main() -> None:
    CASES.mkdir(parents=True, exist_ok=True)
    b1, b2, b3 = BORROWERS["borrower-001"], BORROWERS["borrower-002"], BORROWERS["borrower-003"]
    scenarios: list[dict] = []

    docs1 = write_docs("borrower-001", b1)
    docs2 = write_docs("borrower-002", b2)
    docs3 = write_docs("borrower-003", b3)

    scenarios.append({
        "name": "clean_approval",
        "description": "All four documents agree; FOIR/LTV inside policy; expect APPROVE.",
        "policy_profile": "default",
        "application": {**application("APP-CLEAN-001", b1), "documents": docs1},
        "expected": {"status": "completed", "decision": "approved", "reason_codes_include": [],
                     "reason_codes_exclude": ["HIGH_FOIR", "HIGH_LTV", "INCOME_MISMATCH"]},
    })
    scenarios.append({
        "name": "income_mismatch",
        "description": "Declared income 45,000 vs bank credits 38,500 (13.5% gap) -> INCOME_MISMATCH -> REFER.",
        "policy_profile": "default",
        "application": {**application("APP-MISMATCH-002", b2, product="ev_three_wheeler"), "documents": docs2},
        "expected": {"status": "completed", "decision": "referred", "reason_codes_include": ["INCOME_MISMATCH"]},
    })
    scenarios.append({
        "name": "high_foir",
        "description": "Income 22,000, EMI obligations 6,000, loan 150,000 @16% for 24m -> FOIR > 0.50 -> REJECT.",
        "policy_profile": "default",
        "application": {**application("APP-FOIR-003", b3), "documents": docs3},
        "expected": {"status": "completed", "decision": "declined", "reason_codes_include": ["HIGH_FOIR"]},
    })
    b4 = {**b1, "loan": 115000}
    docs4 = [
        {**d, "text": d["text"].replace("Loan amount requested: Rs 90,000", "Loan amount requested: Rs 115,000")}
        for d in docs1
    ]
    scenarios.append({
        "name": "high_ltv",
        "description": "Loan 115,000 against a 120,000 vehicle -> LTV 0.96 > 0.80 -> REJECT.",
        "policy_profile": "default",
        "application": {**application("APP-LTV-004", b4, loan=115000, tenure=48), "documents": docs4},
        "expected": {"status": "completed", "decision": "declined", "reason_codes_include": ["HIGH_LTV"]},
    })
    docs5 = write_docs("borrower-001", b1, damaged_bank=True)
    scenarios.append({
        "name": "low_confidence",
        "description": "Bank statement scan is damaged (ocr_confidence 0.5, income line illegible) -> "
                       "critical field below threshold -> workflow PAUSES for human review; "
                       "after correction it completes with APPROVE.",
        "policy_profile": "default",
        "application": {**application("APP-LOWCONF-005", b1), "documents": docs5},
        "expected": {"status": "awaiting_human", "decision": "human_review",
                     "low_confidence_fields_include": ["monthly_income"]},
        "resume": {
            "reviewer": "demo.reviewer",
            "reviews": [
                {"field": "monthly_income", "action": "correct", "corrected_value": 38900,
                 "note": "Read directly from the original statement"},
                {"field": "existing_monthly_obligations", "action": "accept", "note": "Matches EMI line"},
            ],
        },
        "expected_after_resume": {"status": "completed", "decision": "approved"},
    })
    docs6 = write_docs("borrower-001", b1, name_on_kyc="Ravi Kumaar")
    scenarios.append({
        "name": "identity_mismatch",
        "description": "KYC name 'Ravi Kumaar' vs bank/invoice 'Ravi Kumar' -> NAME_MISMATCH -> REFER.",
        "policy_profile": "default",
        "application": {**application("APP-IDENTITY-006", b1), "documents": docs6},
        "expected": {"status": "completed", "decision": "referred", "reason_codes_include": ["NAME_MISMATCH"]},
    })
    docs7 = write_docs("borrower-001", b1, skip=("dealer_invoice",))
    scenarios.append({
        "name": "missing_document",
        "description": "No dealer invoice uploaded -> MISSING_DOCUMENT -> REFER (curable by upload).",
        "policy_profile": "default",
        "application": {**application("APP-MISSING-007", b1), "documents": docs7},
        "expected": {"status": "completed", "decision": "referred", "reason_codes_include": ["MISSING_DOCUMENT"]},
    })
    scenarios.append({
        "name": "what_if_approval",
        "description": "Base run is the high_foir REJECT; what-if with tenure 48m lowers EMI so FOIR < 0.50 -> "
                       "scenario APPROVE while the base run stays REJECT (immutable).",
        "policy_profile": "default",
        "application": {**application("APP-WHATIF-008", b3), "documents": docs3},
        "expected": {"status": "completed", "decision": "declined", "reason_codes_include": ["HIGH_FOIR"]},
        "what_if": {"overrides": {"tenure_months": 48}, "find_min_change": True},
        "expected_what_if": {"decision": "approved", "base_decision": "declined", "min_change_found": True},
    })
    scenarios.append({
        "name": "low_age",
        "description": "Borrower aged 19 with clean documents -> LOW_AGE blocker -> REJECT under default policy; "
                       "APPROVE under the aggressive profile (min age 18).",
        "policy_profile": "default",
        "application": {**application("APP-AGE-009", b1, age=19), "documents": docs1},
        "expected": {"status": "completed", "decision": "declined", "reason_codes_include": ["LOW_AGE"]},
        "alternate_policy": {"policy_profile": "aggressive", "expected_decision": "approved"},
    })

    for sc in scenarios:
        (CASES / f"{sc['name']}.json").write_text(json.dumps(sc, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = ["| Scenario | Expected | Reason codes | Notes |", "|---|---|---|---|"]
    for sc in scenarios:
        exp = sc.get("expected", {})
        rows.append(f"| `{sc['name']}` | {exp.get('status')} / **{exp.get('decision')}** | "
                    f"{', '.join(exp.get('reason_codes_include', [])) or '—'} | {sc['description']} |")
    (CASES / "README.md").write_text(
        "# Underwriting scenario fixtures (SYNTHETIC)\n\n"
        "Generated by `python sample-data/generate_sample_data.py`. Each JSON file is a ready-to-POST\n"
        "`/underwrite` payload (`application` + inline `documents`) with the expected outcome, consumed\n"
        "by `ai-service/tests/test_scenarios.py` and `backend/tests/test_underwriting.py`.\n\n"
        + "\n".join(rows) + "\n\n"
        "Decision matrix: any **blocker** reason → `declined`; any **warning** → `referred`; a critical field\n"
        "below the policy confidence threshold pauses the run as `awaiting_human` (`human_review`).\n",
        encoding="utf-8",
    )
    print(f"wrote {len(scenarios)} scenarios to {CASES} and documents to {SAMPLE}/borrower-00N")


if __name__ == "__main__":
    main()
