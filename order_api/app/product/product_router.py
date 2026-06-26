from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.product import product_service
from app.product.product_schema import (ProductCreate, ProductDetail, ProductSummary, ProductUpdate)
from app.core.auth import get_current_merchant, get_current_user
from app.merchant.merchant_model import Merchant
from app.user.user_model import UserRole

router = APIRouter(prefix="/products", tags=["Products"])

# get
@router.get("/", response_model=List[ProductSummary])
def list_products(
    merchant_id: Optional[int] = Query(None),
    search:      Optional[str] = Query(None),
    offset:      int = Query(0, ge=0),
    limit:       int = Query(20, ge=1, le=100),
    only_active_merchant: bool = Query(
        True,
        description="Hanya product dari merchant ACTIVE. Set False di panel merchant untuk mengelola menu sendiri.",
    ),
    db: Session = Depends(get_db),
):
    return product_service.get_products(
        db,
        merchant_id=merchant_id,
        search=search,
        offset=offset,
        limit=limit,
        only_active_merchant=only_active_merchant,
    )


@router.get("/{product_id}", response_model=ProductDetail, summary="Detail product beserta info merchant")
def detail_product(product_id: int, db: Session = Depends(get_db)):
    return product_service.get_product_or_404(db, product_id)


# create
@router.post("/", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    current_merchant: Merchant = Depends(get_current_merchant), 
    db: Session = Depends(get_db),
):
    data.merchant_id = current_merchant.id
    return product_service.create_product(db, data)

# update
@router.put("/{product_id}", response_model=ProductDetail)
def update_product(
    product_id: int,
    data: ProductUpdate,
    current_merchant: Merchant = Depends(get_current_merchant),  
    db: Session = Depends(get_db),
):
    product = product_service.get_product_or_404(db, product_id)
    if product.merchant_id != current_merchant.id:
        raise HTTPException(403, "Anda tidak berhak mengubah produk ini")
    return product_service.update_product(db, product_id, data)


# delete
@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    current_user=Depends(get_current_user),  # admin ATAU merchant pemilik
    db: Session = Depends(get_db),
):
    """Hapus produk. Boleh dilakukan admin (produk apa pun) atau merchant
    pemilik produk tersebut. Produk yang sudah pernah dipakai transaksi ditolak
    di service (409) — sarankan nonaktifkan saja."""
    product = product_service.get_product_or_404(db, product_id)

    if current_user.role == UserRole.ADMIN:
        pass  # admin boleh menghapus produk milik siapa pun
    elif current_user.role == UserRole.MERCHANT:
        merchant = current_user.merchant
        if not merchant or product.merchant_id != merchant.id:
            raise HTTPException(403, "Anda tidak berhak menghapus produk ini")
    else:
        raise HTTPException(403, "Akses ditolak")

    return product_service.delete_product(db, product_id)