"""Logika bisnis untuk Merchant."""
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


def get_merchants(db: Session) -> List[models.Merchant]:
    """Ambil semua merchant, diurutkan berdasarkan nama."""
    return db.query(models.Merchant).order_by(models.Merchant.nama).all()


def get_merchant_or_404(db: Session, merchant_id: int) -> models.Merchant:
    """Ambil satu merchant (beserta relasi products) atau 404 bila tidak ada."""
    merchant = (
        db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    )
    if not merchant:
        raise HTTPException(
            status_code=404,
            detail=f"Merchant dengan ID {merchant_id} tidak ditemukan",
        )
    return merchant
