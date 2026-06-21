from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.auth import get_current_merchant, require_admin
from app.core.database import get_db
from app.merchant import merchant_service
from app.merchant.merchant_model import Merchant
from app.merchant.merchant_schema import (MerchantCreate, MerchantDetail, MerchantSelfUpdate, MerchantSummary, MerchantUpdate)

router = APIRouter(prefix="/merchants", tags=["Merchants"])
 
# get
@router.get("/", response_model=List[MerchantSummary], summary="List semua merchant")
def list_merchants(
    offset: int = Query(0, ge=0, description="Offset untuk pagination"),
    limit: int = Query(20, ge=1, le=100, description="Jumlah item per halaman (maks 100)"),
    search: Optional[str] = Query(None, description="Cari berdasarkan nama merchant"),
    db: Session = Depends(get_db),
):
    return merchant_service.get_merchants(db, offset=offset, limit=limit, search=search)
 
 
@router.get("/{merchant_id}", response_model=MerchantDetail, summary="Detail merchant beserta daftar product")
def detail_merchant(merchant_id: int, db: Session = Depends(get_db)):
    """Ambil detail satu merchant dan semua product yang dijualnya."""
    return merchant_service.get_merchant_or_404(db, merchant_id)
 
 
# update profil sendiri — merchant (HARUS didefinisikan sebelum "/{merchant_id}"
# agar path "me" tidak tertangkap sebagai merchant_id)
@router.put("/me", response_model=MerchantDetail, summary="[Merchant] Update profil/toko sendiri")
def update_own_merchant(
    data: MerchantSelfUpdate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """Merchant mengubah profil/toko miliknya sendiri (termasuk ganti password
    & toggle buka/tutup toko). Tidak bisa mengubah status akun (wewenang admin)."""
    return merchant_service.update_own_merchant(db, current_merchant, data)


# update — hanya admin
@router.put("/{merchant_id}", response_model=MerchantDetail, summary="[Admin] Update merchant (partial update)")
def update_merchant(
    merchant_id: int,
    data: MerchantUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Update field merchant. Kirim **hanya field yang ingin diubah**."""
    return merchant_service.update_merchant(db, merchant_id, data)


# delete — hanya admin
@router.delete("/{merchant_id}", summary="[Admin] Hapus merchant beserta semua product-nya")
def delete_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Hapus merchant dan **semua product** miliknya (cascade delete)."""
    return merchant_service.delete_merchant(db, merchant_id)
