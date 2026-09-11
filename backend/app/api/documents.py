"""Document upload / retrieval routes — Team A.

POST   /applications/{id}/documents
GET    /applications/{id}/documents
DELETE /documents/{document_id}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.document import DocumentOut
from app.services import document_service
from app.services.auth_service import current_user

router = APIRouter()          # mounted under /applications
delete_router = APIRouter()   # mounted at root


@router.post("/{application_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(application_id: str, file: UploadFile = File(...), category: str | None = Form(default=None),
                          ocr_confidence: float | None = Form(default=None), db: Session = Depends(get_db),
                          user: dict | None = Depends(current_user)):
    """Upload a document (pdf/png/jpg/txt, ≤ MAX_UPLOAD_MB) for an application.

    ``ocr_confidence`` (0..1) lets a scanning front-end report page quality; images
    OCR'd here get it from Tesseract automatically.
    """
    return await document_service.upload_document(db, application_id, file, category, ocr_confidence=ocr_confidence,
                                                  uploaded_by=(user or {}).get("email"))


@router.get("/{application_id}/documents", response_model=list[DocumentOut])
async def list_documents(application_id: str, db: Session = Depends(get_db)):
    """List documents for an application."""
    return document_service.list_documents(db, application_id)


@delete_router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: str, db: Session = Depends(get_db)) -> Response:
    """Delete a document and its stored bytes."""
    if not document_service.delete_document(db, document_id):
        raise HTTPException(status_code=404, detail="document not found")
    return Response(status_code=204)
