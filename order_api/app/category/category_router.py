from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.category import category_service
from app.category.category_schema import CategoryOut
from app.core.database import get_db

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryOut], summary="List kategori produk global")
def list_categories(db: Session = Depends(get_db)):
    """Daftar kategori global — dipakai merchant saat menandai produk & untuk
    filter di sisi customer. Pengelolaan (CRUD) ada di endpoint admin.
    """
    return category_service.list_categories(db)
