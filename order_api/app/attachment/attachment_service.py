import os
import re
import secrets
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.attachment.attachment_model import Attachment, EntityType
from app.core.config import settings
from app.merchant.merchant_model import Merchant
from app.product.product_model import Product

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE      = 5 * 1024 * 1024  # 5 MB

# Direktori penyimpanan lokal (fallback bila tidak ada token Vercel Blob).
# attachment_service.py ada di app/attachment/ → parents[2] = root order_api.
_BASE_DIR    = Path(__file__).resolve().parents[2]
UPLOAD_DIR   = _BASE_DIR / "static" / "uploads"
_LOCAL_MARKER = "/static/uploads/"


# ── Helper ────────────────────────────────────────────────────────────────────

def _validate(file: UploadFile, contents: bytes) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Hanya JPEG, PNG, atau WebP yang diizinkan")
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "Ukuran file maksimal 5 MB")


def _safe_name(filename: str) -> str:
    """Sanitasi nama file: hanya alnum, titik, strip, garis bawah."""
    name = os.path.basename(filename or "file")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "file"


def _store_file(path: str, contents: bytes, content_type: str) -> str:
    """Simpan file & kembalikan URL publik.

    Pakai Vercel Blob bila token tersedia; jika tidak, simpan ke disk lokal
    (static/uploads) dan layani via /static.
    """
    if settings.blob_read_write_token:
        import vercel_blob  # impor lazy: hanya dibutuhkan bila pakai Vercel Blob
        response = vercel_blob.put(path, contents, {"access": "public"})
        return response["url"]

    rel      = path.replace("\\", "/")
    abs_path = UPLOAD_DIR.joinpath(*rel.split("/"))
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(contents)
    base = settings.static_base_url.rstrip("/")
    return f"{base}{_LOCAL_MARKER}{rel}"


def _delete_stored(url: str) -> None:
    """Hapus file dari Vercel Blob atau disk lokal (best-effort)."""
    if not url:
        return
    if _LOCAL_MARKER in url:
        try:
            rel = url.split(_LOCAL_MARKER, 1)[1]
            abs_path = UPLOAD_DIR.joinpath(*rel.split("/"))
            if abs_path.exists():
                abs_path.unlink()
        except Exception:
            pass
        return
    try:
        import vercel_blob  # impor lazy
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
        _delete_stored(old.url)
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

    fname = _safe_name(file.filename)
    path  = f"products/{merchant.id}/{product_id}/{fname}"
    url   = _store_file(path, contents, file.content_type)

    att = Attachment(
        url          = url,
        filename     = fname,
        content_type = file.content_type,
        size         = len(contents),
        entity_type  = EntityType.PRODUCT.value,
        entity_id    = product_id,
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

    fname = _safe_name(file.filename)
    path  = f"merchants/{merchant.id}/logo/{fname}"
    url   = _store_file(path, contents, file.content_type)

    att = Attachment(
        url          = url,
        filename     = fname,
        content_type = file.content_type,
        size         = len(contents),
        entity_type  = EntityType.MERCHANT.value,
        entity_id    = merchant.id,
        uploaded_by  = merchant.id,
    )
    db.add(att)
    db.flush()

    merchant.foto = att.url
    db.commit()
    db.refresh(att)
    return att


async def store_image(file: UploadFile, path_prefix: str) -> str:
    """Simpan satu gambar & kembalikan URL publiknya — TANPA baris Attachment/DB.

    Dipakai untuk gambar yang URL-nya disimpan langsung di kolom tabel lain
    (mis. banners.image_url), bukan lewat tabel attachment polymorphic. Prefix
    acak mencegah file dengan nama sama saling menimpa.
    """
    contents = await file.read()
    _validate(file, contents)
    fname = _safe_name(file.filename)
    path  = f"{path_prefix}/{secrets.token_hex(4)}/{fname}"
    return _store_file(path, contents, file.content_type)


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


def list_for_entity(
    db: Session,
    entity_type: str,
    entity_id: int,
) -> List[Attachment]:
    """Ambil semua attachment milik satu baris di tabel mana pun.

    Pengganti relationship: karena polymorphic, attachment tidak bisa di-load
    lewat satu relationship() ke banyak tabel, jadi dilookup manual di sini.
    """
    return (
        db.query(Attachment)
        .filter(
            Attachment.entity_type == entity_type,
            Attachment.entity_id   == entity_id,
        )
        .order_by(Attachment.created_at.desc())
        .all()
    )


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

    _delete_stored(att.url)
    db.delete(att)
    db.commit()
    return {"message": "Attachment berhasil dihapus", "id": attachment_id}