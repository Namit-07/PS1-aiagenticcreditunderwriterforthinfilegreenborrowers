"""Risk reasoning + decision + explanation agents (Team B).

Risk reasoning reads deterministic financials + XGBoost signal + reconciliation and
produces structured strengths/risks/uncertainties (LLM-assisted, never inventing numbers).
The decision agent applies policy-as-config guardrails to reach APPROVE/REFER/REJECT.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings


class RiskReasoningAgent:
    """Structured risk narrative over verified inputs."""

    async def reason(self, context: dict[str, Any]) -> dict[str, Any]:
        financials = context.get("financials", {}) or {}
        risk = context.get("risk", {}) or {}
        recon = context.get("reconciliation", {}) or {}
        foir = float(financials.get("foir", 0.0))
        ltv = float(financials.get("ltv", 0.0))
        band = str(risk.get("risk_band", "MEDIUM"))
        strengths, risks, uncertainties = [], [], []
        if foir <= 0.4:
            strengths.append(f"FOIR {foir:.0%} is comfortably serviceable")
        if ltv <= 0.8:
            strengths.append(f"LTV {ltv:.0%} leaves borrower equity cushion")
        if foir > 0.5:
            risks.append(f"FOIR {foir:.0%} strains monthly cash flow")
        if ltv > 0.85:
            risks.append(f"LTV {ltv:.0%} implies thin collateral cover")
        for item in recon.get("items", []) or []:
            risks.append(f"{item.get('type')}: {item.get('description')}")
        if float(financials.get("income_volatility", 0.0)) > 0.25:
            uncertainties.append("Gig income shows high month-to-month volatility")
        level = "LOW" if band == "LOW" and not risks else ("HIGH" if band == "HIGH" or foir > 0.6 else "MEDIUM")
        reasoning = [
            f"Deterministic FOIR {foir:.2%}, LTV {ltv:.2%}; XGBoost band {band} "
            f"(score {risk.get('risk_score')})."
        ]
        if not get_settings().MOCK_AI_MODE:
            try:
                from app.llm.client import LLMClient
                from app.llm.prompts import RISK_SYSTEM

                parsed = await LLMClient().complete_json(
                    RISK_SYSTEM, f"Summarise risk as JSON given {context}".__str__()[:2000]
                )
                if isinstance(parsed, dict) and parsed.get("reasoning"):
                    reasoning = list(parsed["reasoning"]) if isinstance(parsed["reasoning"], list) else [str(parsed["reasoning"])]
            except Exception:
                pass
        return {"risk_level": level, "strengths": strengths, "risks": risks,
                "uncertainties": uncertainties, "reasoning": reasoning,
                "evidence_refs": [i.get("type") for i in (recon.get("items", []) or [])]}


class DecisionAgent:
    """Policy evaluation into an underwriting decision (Team B)."""

    def __init__(self, policy: dict[str, Any] | None = None) -> None:
        self.policy = policy or {}

    async def decide(
        self,
        financials: dict[str, Any],
        evidence_status: dict[str, Any],
        application: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deterministic policy decision.

        Decision matrix: any blocker -> REJECT; any warning / human flag -> REFER;
        otherwise APPROVE. Reason codes follow ``shared/reason_codes.yaml``.
        """
        from app.policy import engine as policy_engine

        violations = policy_engine.income_violations(financials, self.policy)
        violations += policy_engine.financial_violations(financials, self.policy)
        violations += policy_engine.application_violations(application or {}, self.policy)
        violations += policy_engine.confidence_violations(
            {"overall": float(evidence_status.get("overall_confidence", 1.0))}, self.policy
        )
        income_conf = evidence_status.get("income_confidence")
        income_min = float((self.policy.get("confidence", {}) or {}).get("income_min", 0.6))
        if income_conf is not None and float(income_conf) < income_min:
            violations.append({"code": "LOW_INCOME_CONFIDENCE", "severity": "warning",
                               "message": f"Income confidence {float(income_conf):.2f} below {income_min:.2f}",
                               "field": "monthly_income"})
        for item in evidence_status.get("mismatches", []) or []:
            sev = str(item.get("severity", "")).upper()
            code = str(item.get("type", "INCOME_MISMATCH"))
            if sev == "HIGH" or (sev == "MEDIUM" and code == "INCOME_MISMATCH"):
                violations.append({"code": code,
                                   "severity": "warning",
                                   "message": str(item.get("description", "")),
                                   "field": "reconciliation"})
        if evidence_status.get("human_review_required"):
            violations.append({"code": "HUMAN_REVIEW_REQUIRED", "severity": "warning",
                               "message": "Reviewer flagged this application for manual decision",
                               "field": "human_review"})
        # de-duplicate by (code, message)
        seen: set[tuple[str, str]] = set()
        uniq: list[dict[str, Any]] = []
        for v in violations:
            key = (str(v.get("code")), str(v.get("message")))
            if key not in seen:
                seen.add(key)
                uniq.append(v)
        violations = uniq
        blockers = [v for v in violations if v.get("severity") == "blocker"]
        warnings = [v for v in violations if v.get("severity") != "blocker"]
        if blockers:
            decision, conf = "REJECT", 0.82
        elif warnings:
            decision, conf = "REFER", 0.65
        else:
            decision, conf = "APPROVE", 0.88
        return {"decision": decision, "confidence": conf, "reasons": violations,
                "policy": {"profile": self.policy.get("profile", "default"),
                           "version": str(self.policy.get("version", "1.0"))}}


class ExplanationAgent:
    """Credit-memo builder: separates facts vs computed vs AI reasoning vs policy.

    The memo always contains a deterministic, template-written ``narrative``; when an
    LLM provider is configured (Gemini free tier by default) the narrative text is
    rewritten by the model from the SAME verified numbers. If the model call fails or
    is rate-limited the template text stays, so memo generation never blocks.
    """

    async def build_memo(self, bundle: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timezone

        decision = bundle.get("decision", {}) or {}
        approval_path = bundle.get("approval_path")
        narrative = _template_narrative(bundle)
        narrative = await self._llm_narrative(bundle, narrative)
        return {
            "run_id": bundle.get("run_id"),
            "application_id": bundle.get("application_id"),
            "title": "Credit Memo — AI Agentic Underwriter",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": {
                "narrative": narrative,
                "borrower_summary": bundle.get("borrower", {}),
                "extracted_facts": bundle.get("evidence", []),
                "calculated_values": bundle.get("financials", {}),
                "risk_signal": bundle.get("risk", {}),
                "ai_reasoning": bundle.get("risk_reasoning", {}),
                "policy_rules": bundle.get("policy", {}),
                "human_overrides": bundle.get("human_reviews", []),
                "decision": decision,
                "reason_codes": [r.get("code") for r in (decision.get("reasons", []) or [])],
                "approval_path": approval_path,
                "decision_explanation": bundle.get("explanation"),
            },
            "generated_by": "explanation_agent",
        }

    async def _llm_narrative(self, bundle: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
        """Ask the configured LLM to rewrite the narrative from verified facts only."""
        settings = get_settings()
        if settings.MOCK_AI_MODE or settings.llm_provider == "mock":
            return template
        try:
            import json

            from app.llm.client import LLMClient
            from app.llm.prompts import MEMO_NARRATIVE_SYSTEM

            client = LLMClient()
            packet = _narrative_packet(bundle)
            parsed = await client.complete_json(
                MEMO_NARRATIVE_SYSTEM, "Verified facts packet (JSON):\n" + json.dumps(packet, default=str)
            )
            summary = parsed.get("executive_summary")
            explanation = parsed.get("borrower_explanation")
            if not (isinstance(summary, str) and summary.strip() and isinstance(explanation, str) and explanation.strip()):
                out = dict(template)
                out["llm_error"] = client.last_error or parsed.get("error") or "model returned no narrative"
                return out
            drivers = parsed.get("key_drivers")
            steps = parsed.get("next_steps")
            return {
                **template,
                "executive_summary": summary.strip(),
                "borrower_explanation": explanation.strip(),
                "key_drivers": [str(d) for d in drivers][:6] if isinstance(drivers, list) and drivers else template["key_drivers"],
                "next_steps": [str(s) for s in steps][:5] if isinstance(steps, list) and steps else template["next_steps"],
                "generated_by": f"{client.provider}:{client.model_name}",
            }
        except Exception as exc:  # never block memo generation on the model
            out = dict(template)
            out["llm_error"] = f"{type(exc).__name__}: {exc}"
            return out


def _money(v: Any) -> str:
    try:
        return f"₹{float(v):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _pct(v: Any) -> str:
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _narrative_packet(bundle: dict[str, Any]) -> dict[str, Any]:
    """The only facts the LLM may use (numbers pre-formatted so they are copied verbatim)."""
    fin = bundle.get("financials", {}) or {}
    decision = bundle.get("decision", {}) or {}
    risk = bundle.get("risk", {}) or {}
    policy = bundle.get("policy", {}) or {}
    limits = (policy.get("config") or {}).get("limits", {}) or {}
    borrower = bundle.get("borrower", {}) or {}
    ap = bundle.get("approval_path") or None
    inputs = fin.get("calculation_inputs", {}) or {}
    return {
        "decision": decision.get("decision"),
        "reasons": [{"code": r.get("code"), "severity": r.get("severity"), "message": r.get("message")}
                    for r in (decision.get("reasons") or [])],
        "borrower": {"name": borrower.get("full_name"), "employment_type": borrower.get("employment_type"),
                     "age": borrower.get("age")},
        "loan": {"amount": _money(inputs.get("loan_amount")), "tenure_months": inputs.get("tenure_months"),
                 "annual_rate_percent": inputs.get("annual_rate"), "vehicle_price": _money(inputs.get("vehicle_price"))},
        "financials": {"emi": _money(fin.get("emi")), "foir": _pct(fin.get("foir")), "ltv": _pct(fin.get("ltv")),
                       "verified_monthly_income": _money(fin.get("verified_income")),
                       "existing_monthly_obligations": _money(fin.get("existing_obligations")),
                       "income_volatility": _pct(fin.get("income_volatility"))},
        "policy_limits": {"foir_max": _pct(limits.get("foir_max")), "ltv_max": _pct(limits.get("ltv_max")),
                          "profile": policy.get("profile"), "version": policy.get("version")},
        "risk_band": risk.get("risk_band"),
        "reconciliation_flags": [i.get("type") for i in ((bundle.get("reconciliation") or {}).get("items") or [])],
        "human_reviews": len(bundle.get("human_reviews") or []),
        "approval_path": None if not ap else {
            "description": ap.get("description"),
            "changes": ap.get("changes"),
            "resulting_emi": _money((ap.get("financials") or {}).get("emi")),
            "resulting_foir": _pct((ap.get("financials") or {}).get("foir")),
            "resulting_ltv": _pct((ap.get("financials") or {}).get("ltv")),
        },
    }


def _template_narrative(bundle: dict[str, Any]) -> dict[str, Any]:
    """Deterministic narrative used in mock mode and as the fallback for the LLM."""
    p = _narrative_packet(bundle)
    decision = str(p.get("decision") or "referred")
    fin = p["financials"]
    loan = p["loan"]
    name = p["borrower"].get("name") or "The applicant"
    reasons = p["reasons"]
    codes = [r["code"] for r in reasons if r.get("code")]
    ap = p.get("approval_path")
    limits = p["policy_limits"]

    verdict = {"approved": "is approved", "declined": "is declined", "referred": "is referred for manual review",
               "human_review": "is paused for human review"}.get(decision, f"outcome: {decision}")
    summary = (
        f"The request for {loan['amount']} over {loan['tenure_months']} months {verdict} under the "
        f"{limits.get('profile')} policy (v{limits.get('version')}). Verified monthly income is "
        f"{fin['verified_monthly_income']} against existing obligations of {fin['existing_monthly_obligations']}; "
        f"the proposed EMI of {fin['emi']} gives a FOIR of {fin['foir']} (limit {limits['foir_max']}) and an LTV of "
        f"{fin['ltv']} (limit {limits['ltv_max']}). Risk band: {p.get('risk_band') or '—'}."
    )
    if codes:
        summary += " Reason codes: " + ", ".join(codes) + "."

    if decision == "approved":
        explanation = (
            f"{name}, your loan of {loan['amount']} is approved. Your documents agree with each other, and your "
            f"monthly instalment of {fin['emi']} fits within the affordability limit based on the income we verified."
        )
    elif decision == "declined":
        causes: list[str] = []
        if "HIGH_FOIR" in codes:
            causes.append(f"the monthly instalment of {fin['emi']} would take {fin['foir']} of your verified income "
                          f"(our limit is {limits['foir_max']})")
        if "HIGH_LTV" in codes:
            causes.append(f"the loan is {fin['ltv']} of the vehicle price (our limit is {limits['ltv_max']})")
        if "LOW_AGE" in codes:
            causes.append("you are below the minimum age for this product")
        if "MAX_TENURE_EXCEEDED" in codes:
            causes.append("the requested tenure is longer than the policy allows")
        if "NO_VERIFIED_INCOME" in codes:
            causes.append("we could not verify any monthly income from the documents")
        if not causes:
            causes.append("a hard policy rule was not met: " + ", ".join(codes or ["see reason codes"]))
        explanation = (
            f"{name}, we could not approve the loan of {loan['amount']} as requested because "
            + "; and ".join(causes) + "."
        )
        if ap and ap.get("description"):
            explanation += (
                f" The smallest change that would make it approvable is to {ap['description']}, which brings the "
                f"instalment to {ap['resulting_emi']} and FOIR to {ap['resulting_foir']}."
            )
    else:
        explanation = (
            f"{name}, your application for {loan['amount']} needs a manual check before a decision. "
            "Some details in your documents did not fully agree, so an underwriter will review them with you."
        )

    drivers: list[str] = [
        f"FOIR {fin['foir']} vs limit {limits['foir_max']}",
        f"LTV {fin['ltv']} vs limit {limits['ltv_max']}",
        f"Verified income {fin['verified_monthly_income']} (volatility {fin['income_volatility']})",
    ]
    for r in reasons[:3]:
        if r.get("message"):
            drivers.append(f"{r.get('code')}: {r['message']}")

    if decision == "approved":
        steps = ["Issue sanction letter and collect e-mandate for the EMI.", "Archive the credit memo PDF with the file."]
    elif decision == "declined":
        if ap:
            first = f"Offer the borrower the approvable alternative: {ap['description']}."
        elif "LOW_AGE" in codes:
            first = "Re-apply once the borrower meets the minimum age, or add an eligible co-applicant."
        elif "MAX_TENURE_EXCEEDED" in codes:
            first = "Re-apply with a tenure within the policy maximum."
        elif "NO_VERIFIED_INCOME" in codes:
            first = "Collect income evidence (bank statement or platform payouts) and re-run the workflow."
        else:
            first = "No small change to tenure or loan amount makes the file approvable; re-apply with higher verified income or lower existing obligations."
        steps = [first, "Share the plain-language explanation with the borrower."]
    else:
        steps = ["Underwriter to resolve the reconciliation flags with the borrower.",
                 "Re-run the workflow once corrected documents are uploaded."]

    return {
        "executive_summary": summary,
        "borrower_explanation": explanation,
        "key_drivers": drivers[:6],
        "next_steps": steps,
        "generated_by": "template",
        "numbers_source": "deterministic financial engine (formula v1); the narrative never computes figures",
    }
