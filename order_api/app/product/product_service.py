from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.category.category_model import Category
from app.merchant.merchant_model import Merchant
from app.product.product_model import Product
from app.product.product_schema import ProductCreate, ProductUpdate


def _validate_category(db: Session, category_id: Optional[int]) -> None:
    """Pastikan category_id (bila diisi) merujuk ke kategori yang ada."""
    if category_id is None:
        return
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Kategori dengan ID {category_id} tidak ditemukan")
 
 
def get_products(db: Session, offset: int = 0, limit: int = 20, merchant_id: Optional[int] = None, search: Optional[str] = None) -> List[Product]:
    """Ambil daftar product dengan optional filter & pagination.
    Args:
        offset:        Offset pagination.
        limit:       Maks record (maks 100).
        merchant_id: Filter hanya product milik merchant ini.
        search:      Pencarian substring pada nama product.
    """
    limit = min(limit, 100)
    query = db.query(Product).order_by(Product.nama)
 
    if merchant_id is not None:
        query = query.filter(Product.merchant_id == merchant_id)
 
    if search:
        query = query.filter(Product.nama.ilike(f"%{search}%"))
 
    return query.offset(offset).limit(limit).all()
 
 
def get_product_or_404(db: Session, product_id: int) -> Product:
    """Ambil satu product atau 404 bila tidak ada."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product dengan ID {product_id} tidak ditemukan",
        )
    return product
 
 
def create_product(db: Session, data: ProductCreate) -> Product:
    """Buat product baru. merchant_id harus ada di database (404 jika tidak)."""
    merchant = db.query(Merchant).filter(Merchant.id == data.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail=f"Merchant dengan ID {data.merchant_id} tidak ditemukan")

    _validate_category(db, data.category_id)

    product = Product(
        nama=data.nama,
        deskripsi=data.deskripsi,
        foto=data.foto,
        harga=data.harga,
        stok=data.stok,
        merchant_id=data.merchant_id,
        category_id=data.category_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
 
 
def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    """Update field product (partial update). Hanya field yang dikirim client yang akan diubah."""
    product = get_product_or_404(db, product_id)

    update_fields = data.model_dump(exclude_unset=True)
    if "category_id" in update_fields:
        _validate_category(db, update_fields["category_id"])
    for field, value in update_fields.items():
        setattr(product, field, value)
 
    db.commit()
    db.refresh(product)
    return product
 
 
def delete_product(db: Session, product_id: int) -> dict:
    """Hapus satu product."""
    product = get_product_or_404(db, product_id)
    nama = product.nama
 
    db.delete(product)
    db.commit()
 
    return {"message": f"Product '{nama}' berhasil dihapus", "id": product_id}