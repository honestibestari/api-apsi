"""Logika bisnis kategori produk GLOBAL (dikelola admin).

Kategori tidak lagi menempel ke merchant — satu daftar master dipakai semua
tenant saat menandai produk.
"""
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.category.category_model import Category
from app.category.category_schema import CategoryCreate, CategoryUpdate


def list_categories(db: Session) -> List[Category]:
    return db.query(Category).order_by(Category.nama_kategori).all()


def get_category_or_404(db: Session, category_id: int) -> Category:
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Kategori tidak ditemukan")
    return cat


def create_category(db: Session, data: CategoryCreate) -> Category:
    existing = db.query(Category).filter(
        Category.nama_kategori == data.nama_kategori
    ).first()
    if existing:
        raise HTTPException(409, f"Kategori '{data.nama_kategori}' sudah ada")
    cat = Category(nama_kategori=data.nama_kategori)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def update_category(db: Session, category_id: int, data: CategoryUpdate) -> Category:
    cat = get_category_or_404(db, category_id)
    if data.nama_kategori:
        nama = data.nama_kategori.strip()
        if not nama:
            raise HTTPException(422, "Nama kategori tidak boleh kosong")
        bentrok = db.query(Category).filter(
            Category.nama_kategori == nama,
            Category.id != category_id,
        ).first()
        if bentrok:
            raise HTTPException(409, f"Kategori '{nama}' sudah ada")
        cat.nama_kategori = nama
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, category_id: int) -> dict:
    cat = get_category_or_404(db, category_id)
    nama = cat.nama_kategori
    db.delete(cat)
    db.commit()
    return {"message": f"Kategori '{nama}' berhasil dihapus", "id": category_id}
