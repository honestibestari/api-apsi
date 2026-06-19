from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.attachment import attachment_service
from app.attachment.attachment_schema import AttachmentOut
from app.core.auth import get_current_merchant
from app.core.database import get_db
from app.merchant.merchant_model import Merchant

router = APIRouter(prefix="/attachments", tags=["Attachments"])


# ── CREATE — wajib token ──────────────────────────────────────────────────────

@router.post("/product/{product_id}", response_model=AttachmentOut, summary="Upload foto product")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return await attachment_service.upload_product_image(db, product_id, file, current_merchant)


@router.post("/merchant/logo", response_model=AttachmentOut, summary="Upload logo merchant")
async def upload_merchant_logo(
    file: UploadFile = File(...),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return await attachment_service.upload_merchant_logo(db, file, current_merchant)


# ── READ — tanpa token ────────────────────────────────────────────────────────

@router.get("/", response_model=List[AttachmentOut], summary="List attachment (tanpa token)")
def list_attachments(
    merchant_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return attachment_service.list_attachments(db, merchant_id)


@router.get("/{attachment_id}", response_model=AttachmentOut, summary="Detail attachment (tanpa token)")
def get_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
):
    return attachment_service.get_attachment(db, attachment_id)


# ── UPDATE — wajib token ──────────────────────────────────────────────────────

@router.put("/product/{product_id}", response_model=AttachmentOut, summary="Ganti foto product")
async def replace_product_image(
    product_id: int,
    file: UploadFile = File(...),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return await attachment_service.replace_product_image(db, product_id, file, current_merchant)


@router.put("/merchant/logo", response_model=AttachmentOut, summary="Ganti logo merchant")
async def replace_merchant_logo(
    file: UploadFile = File(...),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return await attachment_service.replace_merchant_logo(db, file, current_merchant)


# ── DELETE — wajib token ──────────────────────────────────────────────────────

@router.delete("/{attachment_id}", summary="Hapus attachment")
def delete_attachment(
    attachment_id: int,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return attachment_service.delete_attachment(db, attachment_id, current_merchant)