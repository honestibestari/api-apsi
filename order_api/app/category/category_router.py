from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.category import category_service
from app.category.category_schema import CategoryCreate, CategoryOut, CategoryUpdate
from app.core.auth import get_current_merchant
from app.core.database import get_db
from app.merchant.merchant_model import Merchant

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryOut], summary="List kategori milik merchant")
def list_categories(
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return category_service.list_categories(db, current_merchant.id)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED,
             summary="Buat kategori baru")
def create_category(
    data: CategoryCreate,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return category_service.create_category(db, current_merchant.id, data)


@router.put("/{category_id}", response_model=CategoryOut, summary="Update kategori")
def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return category_service.update_category(db, category_id, current_merchant.id, data)


@router.delete("/{category_id}", summary="Hapus kategori")
def delete_category(
    category_id: int,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return category_service.delete_category(db, category_id, current_merchant.id)