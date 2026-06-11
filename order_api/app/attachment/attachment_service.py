from typing import List, Optional

import vercel_blob
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.attachment.attachment_model import Attachment
from app.merchant.merchant_model import Merchant
from app.product.product_model import Product

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE      = 5 * 1024 * 1024  # 5 MB


# ── Helper ────────────────────────────────────────────────────────────────────

def _validate(file: UploadFile, contents: bytes) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Hanya JPEG, PNG, atau WebP yang diizinkan")
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "Ukuran file maksimal 5 MB")


def _delete_from_vercel(url: str) -> None:
    try:
        vercel_blob.delete(url)
    except Exception:
        pass


def _get_or_404(db: Session, attachment_id: int) -> Attachment:
    att = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(404, "Attachment tidak ditemukan")
    return att


def _hapus_attachment_lama(db: Session, url: str, merchant_id: int) -> None:
    old = db.query(Attachment).filter(
        Attachment.url == url,
        Attachment.uploaded_by == merchant_id,
    ).first()
    if old:
        _delete_from_vercel(old.url)
        db.delete(old)


# ── CREATE ────────────────────────────────────────────────────────────────────

async def upload_product_image(
    db: Session,
    product_id: int,
    file: UploadFile,
    merchant: Merchant,
) -> Attachment:
    """Upload foto product, langsung update kolom foto di product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product tidak ditemukan")
    if product.merchant_id != merchant.id:
        raise HTTPException(403, "Product bukan milik merchant ini")

    contents = await file.read()
    _validate(file, contents)

    if product.foto:
        _hapus_attachment_lama(db, product.foto, merchant.id)

    path     = f"products/{merchant.id}/{product_id}/{file.filename}"
    response = vercel_blob.put(path, contents, {"access": "public"})

    att = Attachment(
        url          = response["url"],
        filename     = file.filename,
        content_type = file.content_type,
        size         = len(contents),
        uploaded_by  = merchant.id,
    )
    db.add(att)
    db.flush()

    product.foto = att.url
    db.commit()
    db.refresh(att)
    return att


async def upload_merchant_logo(
    db: Session,
    file: UploadFile,
    merchant: Merchant,
) -> Attachment:
    """Upload logo merchant, langsung update kolom foto di merchant."""
    contents = await file.read()
    _validate(file, contents)

    if merchant.foto:
        _hapus_attachment_lama(db, merchant.foto, merchant.id)

    path     = f"merchants/{merchant.id}/logo/{file.filename}"
    response = vercel_blob.put(path, contents, {"access": "public"})

    att = Attachment(
        url          = response["url"],
        filename     = file.filename,
        content_type = file.content_type,
        size         = len(contents),
        uploaded_by  = merchant.id,
    )
    db.add(att)
    db.flush()

    merchant.foto = att.url
    db.commit()
    db.refresh(att)
    return att


# ── READ ──────────────────────────────────────────────────────────────────────

def get_attachment(db: Session, attachment_id: int) -> Attachment:
    """Ambil satu attachment berdasarkan ID. Tanpa cek kepemilikan — untuk akses publik."""
    return _get_or_404(db, attachment_id)


def list_attachments(
    db: Session,
    merchant_id: Optional[int] = None,
) -> List[Attachment]:
    """List attachment. Tanpa cek kepemilikan — untuk akses publik."""
    query = db.query(Attachment)
    if merchant_id:
        query = query.filter(Attachment.uploaded_by == merchant_id)
    return query.order_by(Attachment.created_at.desc()).all()


# ── UPDATE ────────────────────────────────────────────────────────────────────

async def replace_product_image(
    db: Session,
    product_id: int,
    file: UploadFile,
    merchant: Merchant,
) -> Attachment:
    """Ganti foto product dengan file baru. Foto lama otomatis dihapus."""
    return await upload_product_image(db, product_id, file, merchant)


async def replace_merchant_logo(
    db: Session,
    file: UploadFile,
    merchant: Merchant,
) -> Attachment:
    """Ganti logo merchant dengan file baru. Logo lama otomatis dihapus."""
    return await upload_merchant_logo(db, file, merchant)


# ── DELETE ────────────────────────────────────────────────────────────────────

def delete_attachment(
    db: Session,
    attachment_id: int,
    merchant: Merchant,
) -> dict:
    """Hapus attachment dari Vercel Blob dan database. Hanya milik merchant sendiri."""
    att = _get_or_404(db, attachment_id)
    if att.uploaded_by != merchant.id:
        raise HTTPException(403, "Anda tidak punya akses ke file ini")

    _delete_from_vercel(att.url)
    db.delete(att)
    db.commit()
    return {"message": "Attachment berhasil dihapus", "id": attachment_id}