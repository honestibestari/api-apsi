from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.product import product_service
from app.product.product_schema import ProductDetail, ProductSummary

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=List[ProductSummary], summary="List product")
def list_products(db: Session = Depends(get_db)):
    """Ambil daftar semua product."""
    return product_service.get_products(db)


@router.get("/{product_id}", response_model=ProductDetail, summary="Detail product")
def detail_product(product_id: int, db: Session = Depends(get_db)):
    """Ambil detail satu product beserta merchant pemiliknya."""
    return product_service.get_product_or_404(db, product_id)
