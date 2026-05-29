from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.product import product_service
from app.product.product_schema import (ProductCreate, ProductDetail, ProductSummary, ProductUpdate)
from app.core.auth import get_current_merchant
from app.merchant.merchant_model import Merchant

router = APIRouter(prefix="/products", tags=["Products"])

# get
@router.get("/",response_model=List[ProductSummary], summary="List semua product",)
def list_products(
    offset: int = Query(0, ge=0, description="Offset pagination"),
    limit: int = Query(20, ge=1, le=100, description="Jumlah item per halaman"),
    merchant_id: Optional[int] = Query(None, description="Filter product milik merchant ini"),
    search: Optional[str] = Query(None, description="Cari berdasarkan nama product"),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return product_service.get_products(db, merchant_id=current_merchant.id)


@router.get("/{product_id}", response_model=ProductDetail, summary="Detail product beserta info merchant")
def detail_product(product_id: int, db: Session = Depends(get_db)):
    """Ambil detail satu product dan merchant pemiliknya."""
    return product_service.get_product_or_404(db, product_id)


# create
@router.post("/", response_model=ProductDetail, status_code=status.HTTP_201_CREATED, summary="Buat product baru")
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    """ Buat product baru. `merchant_id` wajib diisi dan harus ada di database. """
    return product_service.create_product(db, data)


# update
@router.put("/{product_id}", response_model=ProductDetail, summary="Update product (partial update)")
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    """ Update field product. Kirim hanya field yang ingin diubah. """
    return product_service.update_product(db, product_id, data)


# delete
@router.delete("/{product_id}", summary="Hapus product")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Hapus satu product dari database."""
    return product_service.delete_product(db, product_id)