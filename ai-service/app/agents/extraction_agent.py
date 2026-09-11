"""Extraction agent — turns raw documents into structured evidence (Team B)."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.extraction.document_classifier import classify_document, expected_fields
from app.extraction.pdf_parser import _field_from_text


class ExtractionAgent:
    """Coordinate pdf parsing + OCR + classification to extract evidence items."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.evidence: list[dict[str, Any]] = []

    async def run(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract evidence from a list of source documents.

        Each document: {document_id|filename|storage_key, kind?, text?, pages?}.
        Deterministic regex path always runs (₹0); the LLM only enriches labels.
        """
        out: list[dict[str, Any]] = []
        for doc in documents or []:
            source = str(
                doc.get("document_id") or doc.get("filename") or doc.get("storage_key") or "document"
            )
            preview = str(doc.get("text") or doc.get("text_preview") or "")
            pages = doc.get("pages") or ([{"page": 1, "text": preview}] if preview else [])
            dtype = str(doc.get("kind") or doc.get("category") or "").strip() or classify_document(
                source, preview
            )
            if dtype not in ("kyc", "bank_statement", "dealer_invoice", "platform_earnings"):
                dtype = classify_document(source, preview)
            # OCR engines report a page/document quality score; scale field confidence by it
            try:
                quality = float(doc.get("ocr_confidence", 1.0) or 1.0)
            except (TypeError, ValueError):
                quality = 1.0
            quality = max(0.0, min(1.0, quality))
            for page in pages:
                text = str(page.get("text", "") if isinstance(page, dict) else page or "")
                pno = page.get("page", 1) if isinstance(page, dict) else 1
                for field in expected_fields(dtype):
                    item = _field_from_text(field, text, source, pno)
                    if item:
                        item["kind"] = dtype
                        item["confidence"] = round(float(item["confidence"]) * quality, 3)
                        out.append(item)
            # never silently invent: if nothing found, record a null placeholder
            if not any(e.get("source_document") == source for e in out):
                out.append(
                    {
                        "field": expected_fields(dtype)[0] if expected_fields(dtype) else "monthly_income",
                        "value": None,
                        "source_document": source,
                        "page": None,
                        "confidence": 0.0,
                        "evidence": f"No parseable text in {source}",
                        "kind": dtype,
                    }
                )
        if not self.settings.MOCK_AI_MODE:
            out = await self._enrich_with_llm(out, documents)
        self.evidence = out
        return out

    async def _enrich_with_llm(
        self, items: list[dict[str, Any]], documents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Best-effort LLM relabel; numeric values stay deterministic."""
        try:
            from app.llm.client import LLMClient
            from app.llm.prompts import EXTRACTION_SYSTEM

            client = LLMClient()
            for item in items:
                if item.get("value") is None:
                    continue
                parsed = await client.complete_json(
                    EXTRACTION_SYSTEM,
                    f"Field {item['field']} value {item['value']} evidence: {item.get('evidence','')[:400]}. "
                    "Reply JSON {\"field\":..., \"confidence\": 0..1}.",
                )
                if isinstance(parsed.get("confidence"), (int, float)):
                    item["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
        except Exception:
            pass
        return items

    def _classify(self, document: dict[str, Any]) -> str:
        return classify_document(
            str(document.get("filename") or document.get("document_id") or ""),
            str(document.get("text") or document.get("text_preview") or ""),
        )