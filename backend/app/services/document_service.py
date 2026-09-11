"""Document storage/retrieval business logic (Team A).

Validation: extension + size. Bytes go to local storage (``UPLOAD_DIR``) by default;
the storage key is what a Supabase/S3 backend would use so swapping is a one-liner.
Text is extracted here (txt / PDF via PyMuPDF / images via Tesseract when available)
and shipped to the AI service — the backend never interprets it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Application, Document

settings = get_settings()

CATEGORIES = ("kyc", "bank_statement", "dealer_invoice", "platform_earnings", "other")
_CONTENT_TYPES = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                  "txt": "text/plain"}


def _ext(name: str) -> str:
    return (name.rsplit(".", 1)[-1].lower() if "." in name else "")


def _guess_category(file_name: str) -> str:
    low = file_name.lower()
    if "bank" in low or "statement" in low:
        return "bank_statement"
    if "invoice" in low or "dealer" in low:
        return "dealer_invoice"
    if "platform" in low or "earning" in low or "payout" in low:
        return "platform_earnings"
    if "kyc" in low or "aadhaar" in low or "pan" in low or "id" in low:
        return "kyc"
    return "other"


def extract_text(data: bytes, ext: str) -> tuple[str, float | None]:
    """Best-effort text extraction -> (text, ocr_confidence|None)."""
    if ext == "txt":
        return data.decode("utf-8", errors="replace"), None
    if ext == "pdf":
        try:
            import fitz  # type: ignore

            doc = fitz.open(stream=data, filetype="pdf")
            text = "\n".join((p.get_text("text") or "") for p in doc)
            doc.close()
            if text.strip():
                return text, None
        except Exception:
            pass
        return "", None
    if ext in ("png", "jpg", "jpeg"):
        try:
            import io

            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore

            img = Image.open(io.BytesIO(data))
            text = pytesseract.image_to_string(img)
            try:
                d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                confs = [float(c) for c in d.get("conf", []) if str(c) not in ("-1", "")]
                conf = round(sum(confs) / len(confs) / 100.0, 3) if confs else None
            except Exception:
                conf = None
            return text, conf
        except Exception:
            return "", None
    return "", None


def validate_upload(file_name: str, size: int) -> str:
    ext = _ext(file_name)
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"unsupported file type '.{ext}'; allowed: "
                                                    f"{', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS)}")
    if size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"file exceeds {settings.MAX_UPLOAD_MB} MB limit")
    if size == 0:
        raise HTTPException(status_code=422, detail="empty file")
    return ext


def _store_bytes(application_id: str, document_id: str, file_name: str, data: bytes) -> str:
    key = f"{application_id}/{document_id}_{Path(file_name).name}"
    if settings.STORAGE_BACKEND == "local":
        path = Path(settings.UPLOAD_DIR) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    else:  # pragma: no cover - S3/Supabase wiring point
        raise HTTPException(status_code=501, detail=f"storage backend {settings.STORAGE_BACKEND} not configured")
    return key


async def upload_document(db: Session, application_id: str, file: UploadFile, category: str | None = None,
                          ocr_confidence: float | None = None, uploaded_by: str | None = None) -> dict[str, Any]:
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="application not found")
    data = await file.read()
    file_name = file.filename or "upload"
    ext = validate_upload(file_name, len(data))
    if category and category not in CATEGORIES:
        raise HTTPException(status_code=422, detail=f"category must be one of {', '.join(CATEGORIES)}")
    if ocr_confidence is not None and not 0.0 <= ocr_confidence <= 1.0:
        raise HTTPException(status_code=422, detail="ocr_confidence must be between 0 and 1")
    category = category or _guess_category(file_name)
    text, ocr_conf = extract_text(data, ext)
    if ocr_confidence is not None:
        ocr_conf = ocr_confidence
    doc = Document(application_id=application_id, file_name=file_name, category=category,
                   content_type=file.content_type or _CONTENT_TYPES.get(ext), size_bytes=len(data),
                   extracted_text=text or None, text_preview=(text or "")[:400] or None,
                   ocr_confidence=str(ocr_conf) if ocr_conf is not None else None, uploaded_by=uploaded_by,
                   storage_key="pending")
    db.add(doc)
    db.flush()
    doc.storage_key = _store_bytes(application_id, doc.id, file_name, data)
    if app.status in ("draft", "documents_pending"):
        app.status = "documents_pending"
    db.commit()
    db.refresh(doc)
    return doc.to_dict()


def list_documents(db: Session, application_id: str) -> list[dict[str, Any]]:
    rows = db.query(Document).filter(Document.application_id == application_id).order_by(Document.uploaded_at).all()
    return [r.to_dict() for r in rows]


def delete_document(db: Session, document_id: str) -> bool:
    doc = db.get(Document, document_id)
    if not doc:
        return False
    if settings.STORAGE_BACKEND == "local":
        try:
            (Path(settings.UPLOAD_DIR) / doc.storage_key).unlink(missing_ok=True)
        except Exception:
            pass
    db.delete(doc)
    db.commit()
    return True
