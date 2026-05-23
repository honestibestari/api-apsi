from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.core.database import get_db
from app.services import merchant_service

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.get("/", response_model=List[schemas.MerchantSummary], summary="List merchant")
def list_merchants(db: Session = Depends(get_db)):
    """Ambil daftar semua merchant."""
    return merchant_service.get_merchants(db)


@router.get("/{merchant_id}", response_model=schemas.MerchantDetail, summary="Detail merchant")
def detail_merchant(merchant_id: int, db: Session = Depends(get_db)):
    """Ambil detail merchant beserta daftar product yang dijual."""
    return merchant_service.get_merchant_or_404(db, merchant_id)
