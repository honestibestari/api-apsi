from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.auth import hash_password
from app.merchant.merchant_model import Merchant
from app.merchant.merchant_schema import MerchantCreate, MerchantSelfUpdate, MerchantUpdate


def get_merchants(db: Session, offset: int = 0, limit: int = 20, search: Optional[str] = None) -> List[Merchant]:
    """Ambil daftar merchant dengan optional pagination & pencarian nama.

    Args:
        offset:   Offset (untuk pagination). Default 0.
        limit:  Jumlah maksimum record. Default 20, maks 100.
        search: Substring pencarian pada kolom 'nama' (case-insensitive).
    """
    limit = min(limit, 100)  
    query = db.query(Merchant).order_by(Merchant.nama)

    if search:
        query = query.filter(Merchant.nama.ilike(f"%{search}%"))

    return query.offset(offset).limit(limit).all()


def get_merchant_or_404(db: Session, merchant_id: int) -> Merchant:
    """Ambil satu merchant atau 404 bila tidak ada."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=404,
            detail=f"Merchant dengan ID {merchant_id} tidak ditemukan",
        )
    return merchant


def create_merchant(db: Session, data: MerchantCreate) -> Merchant:
    """Buat merchant baru dan simpan ke database.
    Duplikat nama diizinkan (merchant berbeda bisa punya nama mirip), tapi bisa ditambahkan validasi unik di sini jika diperlukan.
    """
    merchant = Merchant(**data.model_dump())
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


def update_merchant(db: Session, merchant_id: int, data: MerchantUpdate) -> Merchant:
    """Update field merchant yang dikirim (partial update).
    Hanya field yang tidak None di `data` yang akan diubah, sehingga client bisa kirim hanya field yang ingin diperbarui.
    """
    merchant = get_merchant_or_404(db, merchant_id)

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(merchant, field, value)

    db.commit()
    db.refresh(merchant)
    return merchant


def update_own_merchant(db: Session, merchant: Merchant, data: MerchantSelfUpdate) -> Merchant:
    """Update profil/toko milik merchant sendiri (PUT /merchants/me).

    Berbeda dari update_merchant (admin), di sini:
    - `status` tidak bisa diubah (tidak ada di MerchantSelfUpdate).
    - `password` (bila dikirim) di-hash dan disimpan ke akun User *dan* Merchant.
      Login memverifikasi `user.password_hash`, jadi keduanya harus sinkron.
    """
    update_fields = data.model_dump(exclude_unset=True)

    password = update_fields.pop("password", None)
    if password:
        hashed = hash_password(password)
        merchant.password_hash = hashed
        if merchant.user:
            merchant.user.password_hash = hashed

    for field, value in update_fields.items():
        setattr(merchant, field, value)

    db.commit()
    db.refresh(merchant)
    return merchant


def delete_merchant(db: Session, merchant_id: int) -> dict:
    """Hapus merchant beserta semua product-nya (cascade sudah di-set di model)."""
    merchant = get_merchant_or_404(db, merchant_id)
    nama = merchant.nama

    db.delete(merchant)
    db.commit()

    return {"message": f"Merchant '{nama}' berhasil dihapus", "id": merchant_id}