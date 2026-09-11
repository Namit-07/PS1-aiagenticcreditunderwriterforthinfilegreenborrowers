"""OCR for scanned documents (Team B)."""

from __future__ import annotations

from typing import Any


def ocr_image(image_path: str) -> str:
    """Run OCR on a rasterized/scanned page image (pytesseract + Pillow)."""
    try:
        from PIL import Image
        import pytesseract
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Pillow + pytesseract required for OCR") from exc
    try:
        img = Image.open(image_path)
        return str(pytesseract.image_to_string(img) or "")
    except Exception:
        return ""


def ocr_pdf_page_text(text: str, min_chars: int = 40) -> tuple[bool, str]:
    """Heuristic: True if page text is too sparse and OCR should be attempted."""
    needs = len((text or "").strip()) < min_chars
    return needs, (text or "")


def rasterize_pdf_page(pdf_path: str, page: int, dpi: int = 200) -> Any:
    """Rasterize a PDF page to a temp PNG path for OCR (best-effort)."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        pix = doc[max(0, page - 1)].get_pixmap(dpi=dpi)
        import tempfile, os

        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        pix.save(tmp)
        try:
            doc.close()
        except Exception:
            pass
        return tmp
    except Exception:
        return None