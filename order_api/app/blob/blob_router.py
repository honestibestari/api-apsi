import vercel_blob
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List
 
from app.attachment.attachment_model import Attachment
from app.attachment.attachment_schema import AttachmentOut
from app.core.auth import get_current_merchant
from app.core.database import get_db
from app.merchant.merchant_model import Merchant
from app.product.product_model import Product
 
router = APIRouter(prefix="/upload", tags=["Upload"])
 
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE      = 5 * 1024 * 1024  # 5 MB
 
 
# ── Helper ────────────────────────────────────────────────────────────────────
 
async def _upload_to_blob(
    file: UploadFile,
    path: str,
    db: Session,
    merchant_id: int,
) -> Attachment:
    """Upload file ke Vercel Blob lalu simpan metadata ke tabel attachments."""
 
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Hanya JPEG, PNG, atau WebP yang diizinkan")
 
    contents = await file.read()
 
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "Ukuran file maksimal 5 MB")
 
    response = vercel_blob.put(path, contents, {"access": "public"})
    url      = response["url"]
 
    attachment = Attachment(
        url          = url,
        filename     = file.filename,
        content_type = file.content_type,
        size         = len(contents),
        uploaded_by  = merchant_id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
 
    return attachment
 
 
def _hapus_attachment_lama(db: Session, url: str, merchant_id: int) -> None:
    """Hapus attachment lama dari DB dan Vercel Blob."""
    old = db.query(Attachment).filter(
        Attachment.url == url,
        Attachment.uploaded_by == merchant_id,
    ).first()
    if old:
        try:
            vercel_blob.delete(old.url)
        except Exception:
            pass
        db.delete(old)
 
 
# ── Upload foto product ───────────────────────────────────────────────────────
 
@router.post(
    "/product/{product_id}",
    response_model=AttachmentOut,
    summary="Upload foto product — langsung update kolom foto",
)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Upload foto product. Kalau sudah ada foto lama, otomatis dihapus dulu
    dari Vercel Blob dan DB sebelum upload yang baru.
    Product harus milik merchant yang login.
    """
    # Validasi product milik merchant yang login
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product tidak ditemukan")
    if product.merchant_id != current_merchant.id:
        raise HTTPException(403, "Product bukan milik merchant ini")
 
    # Hapus foto lama jika sudah ada
    if product.foto:
        _hapus_attachment_lama(db, product.foto, current_merchant.id)
 
    # Upload file baru
    path       = f"products/{current_merchant.id}/{product_id}/{file.filename}"
    attachment = await _upload_to_blob(file, path, db, current_merchant.id)
 
    # Update kolom foto di product
    product.foto = attachment.url
    db.commit()
 
    return attachment
 
 
# ── Upload logo merchant ──────────────────────────────────────────────────────
 
@router.post(
    "/merchant/logo",
    response_model=AttachmentOut,
    summary="Upload logo merchant — langsung update profil",
)
async def upload_merchant_logo(
    file: UploadFile = File(...),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Upload logo merchant. Kalau sudah ada logo lama, otomatis dihapus dulu
    dari Vercel Blob dan DB sebelum upload yang baru.
    """
    # Hapus logo lama jika sudah ada
    if current_merchant.foto:
        _hapus_attachment_lama(db, current_merchant.foto, current_merchant.id)
 
    # Upload file baru
    path       = f"merchants/{current_merchant.id}/logo/{file.filename}"
    attachment = await _upload_to_blob(file, path, db, current_merchant.id)
 
    # Update kolom foto di merchant
    current_merchant.foto = attachment.url
    db.commit()
 
    return attachment
 
 
# ── List attachment ───────────────────────────────────────────────────────────
 
@router.get(
    "/attachments",
    response_model=List[AttachmentOut],
    summary="List semua attachment milik merchant yang login",
)
def list_attachments(
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """List semua file yang pernah diupload oleh merchant yang login."""
    return (
        db.query(Attachment)
        .filter(Attachment.uploaded_by == current_merchant.id)
        .order_by(Attachment.created_at.desc())
        .all()
    )
 
 
# ── Hapus attachment ──────────────────────────────────────────────────────────
 
@router.delete(
    "/{attachment_id}",
    summary="Hapus attachment dari DB dan Vercel Blob",
)
def delete_attachment(
    attachment_id: int,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Hapus attachment dari DB dan file dari Vercel Blob sekaligus."""
    attachment = db.query(Attachment).filter(
        Attachment.id == attachment_id,
        Attachment.uploaded_by == current_merchant.id,
    ).first()
 
    if not attachment:
        raise HTTPException(404, "Attachment tidak ditemukan")
 
    try:
        vercel_blob.delete(attachment.url)
    except Exception:
        pass
 
    db.delete(attachment)
    db.commit()
    return {"message": "Attachment berhasil dihapus", "id": attachment_id}