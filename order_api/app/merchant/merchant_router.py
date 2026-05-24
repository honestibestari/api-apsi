from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.merchant import merchant_service
from app.merchant.merchant_schema import MerchantDetail, MerchantSummary

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.get("/", response_model=List[MerchantSummary], summary="List merchant")
def list_merchants(db: Session = Depends(get_db)):
    """Ambil daftar semua merchant."""
    return merchant_service.get_merchants(db)


@router.get("/{merchant_id}", response_model=MerchantDetail, summary="Detail merchant")
def detail_merchant(merchant_id: int, db: Session = Depends(get_db)):
    """Ambil detail merchant beserta daftar product yang dijual."""
    return merchant_service.get_merchant_or_404(db, merchant_id)
