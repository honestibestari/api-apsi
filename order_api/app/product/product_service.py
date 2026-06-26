from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from app.category.category_model import Category
from app.merchant.merchant_model import Merchant, MerchantStatus
from app.product.product_model import Product, ProductAddon
from app.product.product_schema import ProductCreate, ProductUpdate


def _validate_category(db: Session, category_id: Optional[int]) -> None:
    """Pastikan category_id (bila diisi) merujuk ke kategori yang ada."""
    if category_id is None:
        return
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Kategori dengan ID {category_id} tidak ditemukan")


def _sync_addons(product: Product, addons) -> None:
    """Ganti seluruh daftar add-on produk dengan yang dikirim client.

    `addons` None = tidak menyentuh add-on (mis. update tanpa field ini).
    List kosong = hapus semua add-on. delete-orphan menghapus baris lama.
    """
    if addons is None:
        return
    product.additionals.clear()
    for a in addons:
        product.additionals.append(
            ProductAddon(nama=a.nama.strip(), harga=a.harga, is_active=a.is_active)
        )


def get_products(db: Session, offset: int = 0, limit: int = 20, merchant_id: Optional[int] = None, search: Optional[str] = None, only_active_merchant: bool = True) -> List[Product]:
    """Ambil daftar product dengan optional filter & pagination.
    Args:
        offset:        Offset pagination.
        limit:       Maks record (maks 100).
        merchant_id: Filter hanya product milik merchant ini.
        search:      Pencarian substring pada nama product.
        only_active_merchant: Bila True (default), hanya tampilkan product dari
            merchant berstatus ACTIVE. Merchant yang dinonaktifkan/pending/suspended
            tidak boleh muncul di etalase pelanggan. Set False untuk panel merchant
            yang mengelola menunya sendiri tanpa peduli status.
    """
    limit = min(limit, 100)
    query = (
        db.query(Product)
        .options(selectinload(Product.additionals))
        .order_by(Product.nama)
    )

    if only_active_merchant:
        query = query.join(Merchant, Product.merchant_id == Merchant.id).filter(
            Merchant.status == MerchantStatus.ACTIVE
        )

    if merchant_id is not None:
        query = query.filter(Product.merchant_id == merchant_id)

    if search:
        query = query.filter(Product.nama.ilike(f"%{search}%"))

    return query.offset(offset).limit(limit).all()


def get_product_or_404(db: Session, product_id: int) -> Product:
    """Ambil satu product atau 404 bila tidak ada."""
    product = (
        db.query(Product)
        .options(selectinload(Product.additionals))
        .filter(Product.id == product_id)
        .first()
    )
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
        is_available=data.is_available,
        merchant_id=data.merchant_id,
        category_id=data.category_id,
    )
    _sync_addons(product, data.additionals)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    """Update field product (partial update). Hanya field yang dikirim client yang akan diubah."""
    product = get_product_or_404(db, product_id)

    update_fields = data.model_dump(exclude_unset=True)
    # `additionals` ditangani lewat relasi, bukan setattr biasa.
    update_fields.pop("additionals", None)
    if "category_id" in update_fields:
        _validate_category(db, update_fields["category_id"])
    for field, value in update_fields.items():
        setattr(product, field, value)

    if "additionals" in data.model_fields_set:
        _sync_addons(product, data.additionals)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> dict:
    """Hapus satu product.

    Produk yang PERNAH dipakai dalam transaksi (punya OrderItem) tidak boleh
    dihapus — menghapusnya akan merusak riwayat pesanan/laporan. Sarankan
    nonaktifkan saja (is_available=False) lewat pesan error.
    """
    from app.merchant_order.merchant_order_model import OrderItem

    product = get_product_or_404(db, product_id)
    nama = product.nama

    used = (
        db.query(OrderItem.id)
        .filter(OrderItem.product_id == product_id)
        .first()
        is not None
    )
    if used:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Produk '{nama}' sudah pernah dipakai dalam transaksi sehingga "
                "tidak dapat dihapus. Nonaktifkan saja agar tidak bisa dipesan "
                "tanpa menghapus riwayat pesanan."
            ),
        )

    db.delete(product)
    db.commit()

    return {"message": f"Product '{nama}' berhasil dihapus", "id": product_id}
