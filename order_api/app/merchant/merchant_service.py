"""Logika bisnis untuk Merchant."""
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.merchant.merchant_model import Merchant


def get_merchants(db: Session) -> List[Merchant]:
    """Ambil semua merchant, diurutkan berdasarkan nama."""
    return db.query(Merchant).order_by(Merchant.nama).all()


def get_merchant_or_404(db: Session, merchant_id: int) -> Merchant:
    """Ambil satu merchant (beserta relasi products) atau 404 bila tidak ada."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=404,
            detail=f"Merchant dengan ID {merchant_id} tidak ditemukan",
        )
    return merchant
