"""Credit-memo PDF rendering + on-disk cache (Team A).

Pure functions only (no AI-service calls) so both the mirroring code path — which
generates the PDF automatically the moment a run completes — and the download
routes can share them without import cycles.

Rendering uses a tiny dependency-free PDF writer (Helvetica, text only) so the demo
has no native dependencies.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from app.config import get_settings

settings = get_settings()

_LINE_WIDTH = 108
_PER_PAGE = 60


# --------------------------------------------------------------------------- #
# cache location
# --------------------------------------------------------------------------- #
def memo_dir() -> Path:
    d = Path(settings.UPLOAD_DIR).parent / "memos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pdf_path(run_id: str) -> Path:
    return memo_dir() / f"{run_id}.pdf"


def has_pdf(run_id: str) -> bool:
    return pdf_path(run_id).is_file()


def write_memo_pdf(run_id: str, memo: dict[str, Any]) -> Path:
    """Render and store the PDF for ``run_id`` (overwrites any previous file)."""
    path = pdf_path(run_id)
    path.write_bytes(memo_to_pdf(memo))
    return path


def read_memo_pdf(run_id: str) -> bytes | None:
    path = pdf_path(run_id)
    return path.read_bytes() if path.is_file() else None


# --------------------------------------------------------------------------- #
# memo -> lines -> PDF
# --------------------------------------------------------------------------- #
def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".") if abs(v) < 10 else f"{v:,.2f}"
    if isinstance(v, (dict, list)):
        return str(v)[:110]
    return str(v)


def _wrap(text: Any, indent: str = "   ") -> list[str]:
    body = str(text or "").strip()
    if not body:
        return []
    return [indent + ln for ln in textwrap.wrap(body, width=_LINE_WIDTH - len(indent))]


def memo_lines(memo: dict[str, Any]) -> list[str]:
    s = memo.get("sections", {}) or {}
    dec = s.get("decision", {}) or {}
    lines = [memo.get("title", "Credit Memo"), f"Run: {memo.get('run_id')}   Application: {memo.get('application_id')}",
             f"Generated: {memo.get('generated_at')}   by {memo.get('generated_by')}", ""]

    nar = s.get("narrative") or {}
    if nar:
        lines += [f"SUMMARY (narrative by {nar.get('generated_by', 'template')}; all figures from the deterministic engine)"]
        lines += _wrap(nar.get("executive_summary"))
        lines += [""]
        lines += ["   For the borrower:"]
        lines += _wrap(nar.get("borrower_explanation"), indent="     ")
        if nar.get("key_drivers"):
            lines += ["   Key drivers:"]
            for d in nar.get("key_drivers") or []:
                lines += _wrap(f"- {d}", indent="     ")
        if nar.get("next_steps"):
            lines += ["   Next steps:"]
            for d in nar.get("next_steps") or []:
                lines += _wrap(f"- {d}", indent="     ")
        lines.append("")

    lines += ["1. DECISION", f"   Decision: {str(dec.get('decision', '')).upper()}   Confidence: {dec.get('confidence')}",
              "   Reason codes: " + (", ".join(s.get("reason_codes", []) or []) or "none")]
    for r in dec.get("reasons", []) or []:
        lines += _wrap(f"- [{r.get('severity')}] {r.get('code')}: {r.get('message', '')}")
    ho = dec.get("human_override")
    if ho:
        lines += _wrap(f"Human override: {ho.get('from')} -> {ho.get('to')} by {ho.get('reviewer')} ({ho.get('note')})")
    lines.append("")

    ap = s.get("approval_path")
    if str(dec.get("decision", "")).lower() == "declined":
        lines += ["1a. PATH TO APPROVAL (automatic what-if on the immutable base run)"]
        if ap:
            lines += _wrap(f"Minimum change: {ap.get('description')}")
            for k, v in (ap.get("changes") or {}).items():
                lines.append(f"   change.{k}: {_fmt(v)}")
            apf = ap.get("financials") or {}
            lines.append(f"   resulting EMI {_fmt(apf.get('emi'))}   FOIR {_fmt(apf.get('foir'))}   LTV {_fmt(apf.get('ltv'))}"
                         f"   -> {str((ap.get('decision') or {}).get('decision', '')).upper()}")
        else:
            lines += _wrap("No change to tenure (up to the policy maximum) or loan amount (down to -50%) makes this file "
                           "approvable; the blocker is not purely affordability.")
        lines.append("")

    ex = s.get("decision_explanation") or {}
    if ex:
        lines += [f"1b. WHY THIS DECISION (policy margins + SHAP; words by {ex.get('generated_by', 'template')})"]
        lines += _wrap(ex.get("headline"))
        for sent in ex.get("sentences") or []:
            lines += _wrap(sent)
        lines.append("   Mathematics:")
        for ml in ex.get("math_lines") or []:
            lines += _wrap(ml, indent="     ")
        lines.append("")

    b = s.get("borrower_summary", {}) or {}
    lines += ["2. BORROWER SUMMARY (declared facts)"]
    for k in ("ref_id", "full_name", "age", "location_tier", "employment_type", "declared_monthly_income"):
        if k in b:
            lines.append(f"   {k}: {_fmt(b[k])}")
    for k, v in (b.get("loan_request") or {}).items():
        lines.append(f"   loan_request.{k}: {_fmt(v)}")
    lines.append("")
    lines += ["3. EXTRACTED FACTS (evidence with citations)"]
    for e in s.get("extracted_facts", []) or []:
        lines += _wrap(f"{e.get('field')} = {_fmt(e.get('value'))}  conf {e.get('confidence')}  "
                       f"[{e.get('source_document')} p.{e.get('page')}] {e.get('review_status', '')}")
    lines.append("")
    c = s.get("calculated_values", {}) or {}
    lines += ["4. CALCULATED VALUES (deterministic engine, formula " + str(c.get("formula_version")) + ")"]
    for k in ("verified_income", "existing_obligations", "emi", "foir", "ltv", "income_volatility", "income_stability",
              "loan_to_income", "emi_to_income"):
        if k in c:
            lines.append(f"   {k}: {_fmt(c[k])}")
    for k, v in (c.get("calculation_inputs") or {}).items():
        lines.append(f"   input.{k}: {_fmt(v)}")
    lines.append("")
    r = s.get("risk_signal", {}) or {}
    lines += ["5. RISK SIGNAL (secondary, never decides)",
              f"   score {r.get('risk_score')}  band {r.get('risk_band')}  model {r.get('model_version')}/{r.get('model_backend')}", ""]
    ai = s.get("ai_reasoning", {}) or {}
    lines += ["6. AI REASONING"]
    for key in ("strengths", "risks", "uncertainties", "reasoning"):
        for item in ai.get(key, []) or []:
            lines += _wrap(f"{key}: {item}")
    lines.append("")
    p = s.get("policy_rules", {}) or {}
    lines += ["7. POLICY", f"   profile {p.get('profile')} version {p.get('version')}"]
    for k, v in ((p.get("config") or {}).get("limits") or {}).items():
        lines.append(f"   limit.{k}: {_fmt(v)}")
    lines.append("")
    lines += ["8. HUMAN OVERRIDES"]
    hos = s.get("human_overrides", []) or []
    if not hos:
        lines.append("   none")
    for h in hos:
        lines += _wrap(f"{h.get('field')}: {h.get('action')} {_fmt(h.get('original_value'))} -> "
                       f"{_fmt(h.get('corrected_value'))} by {h.get('reviewer')} at {h.get('timestamp')} ({h.get('note')})")
    lines += ["", "SYNTHETIC DATA - demo only. Financial numbers computed deterministically; LLM never sets numbers."]
    return lines


_TRANSLITERATE = {
    "₹": "Rs ", "→": "->", "—": "-", "–": "-", "≥": ">=", "≤": "<=", "Σ": "sum ", "φ": "phi", "÷": "/",
    "×": "x", "•": "-", "…": "...", "≈": "~", "±": "+/-", "‘": "'", "’": "'", "“": '"', "”": '"', "·": "-",
}


def _pdf_escape(text: str) -> str:
    for src, dst in _TRANSLITERATE.items():
        text = text.replace(src, dst)
    # Helvetica (WinAnsi) cannot show other scripts; drop accents where possible, else '?'
    import unicodedata

    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_pdf(lines: list[str], title: str = "Credit Memo") -> bytes:
    """Minimal single-font PDF writer (Helvetica, 10pt, A4, 60 lines/page)."""
    pages = [lines[i:i + _PER_PAGE] for i in range(0, max(1, len(lines)), _PER_PAGE)] or [[]]
    objects: list[bytes] = []

    def add(obj: str | bytes) -> int:
        objects.append(obj.encode("latin-1") if isinstance(obj, str) else obj)
        return len(objects)

    font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []
    for chunk in pages:
        y = 810
        parts = ["BT", "/F1 10 Tf", "12 TL", f"40 {y} Td"]
        for ln in chunk:
            parts.append(f"({_pdf_escape(ln[:120])}) Tj T*")
        parts.append("ET")
        stream = "\n".join(parts)
        cid = add(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        content_ids.append(cid)
        page_ids.append(0)  # placeholder, filled after pages object id is known
    pages_id = len(objects) + len(pages) + 1
    for i, cid in enumerate(content_ids):
        page_ids[i] = add(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] "
                          f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {cid} 0 R >>")
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    real_pages_id = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
    assert real_pages_id == pages_id
    catalog = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
    info = add(f"<< /Title ({_pdf_escape(title)}) /Producer (acu-backend) >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode("latin-1") + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("latin-1")
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n").encode("latin-1")
    return bytes(out)


def memo_to_pdf(memo: dict[str, Any]) -> bytes:
    return render_pdf(memo_lines(memo), title=str(memo.get("title", "Credit Memo")))
