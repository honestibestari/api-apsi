"""Logika bisnis untuk Product."""
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


def get_products(db: Session) -> List[models.Product]:
    """Ambil semua product, diurutkan berdasarkan nama."""
    return db.query(models.Product).order_by(models.Product.nama).all()


def get_product_or_404(db: Session, product_id: int) -> models.Product:
    """Ambil satu product berdasarkan ID, atau 404 bila tidak ada."""
    product = (
        db.query(models.Product).filter(models.Product.id == product_id).first()
    )
    if not product:
        raise HTTPException(
            status_code=404, detail=f"Product dengan ID {product_id} tidak ditemukan"
        )
    return product
