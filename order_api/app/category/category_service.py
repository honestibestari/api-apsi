from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.category.category_model import Category
from app.category.category_schema import CategoryCreate, CategoryUpdate


def list_categories(db: Session, merchant_id: int) -> List[Category]:
    return db.query(Category).filter(Category.id_tenant == merchant_id).all()


def get_category_or_404(db: Session, category_id: int, merchant_id: int) -> Category:
    cat = db.query(Category).filter(
        Category.id == category_id,
        Category.id_tenant == merchant_id
    ).first()
    if not cat:
        raise HTTPException(404, "Kategori tidak ditemukan")
    return cat


def create_category(db: Session, merchant_id: int, data: CategoryCreate) -> Category:
    existing = db.query(Category).filter(
        Category.id_tenant == merchant_id,
        Category.nama_kategori == data.nama_kategori
    ).first()
    if existing:
        raise HTTPException(409, f"Kategori '{data.nama_kategori}' sudah ada")
    cat = Category(nama_kategori=data.nama_kategori, id_tenant=merchant_id)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def update_category(db: Session, category_id: int, merchant_id: int, data: CategoryUpdate) -> Category:
    cat = get_category_or_404(db, category_id, merchant_id)
    if data.nama_kategori:
        cat.nama_kategori = data.nama_kategori.strip()
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, category_id: int, merchant_id: int) -> dict:
    cat = get_category_or_404(db, category_id, merchant_id)
    nama = cat.nama_kategori
    db.delete(cat)
    db.commit()
    return {"message": f"Kategori '{nama}' berhasil dihapus", "id": category_id}