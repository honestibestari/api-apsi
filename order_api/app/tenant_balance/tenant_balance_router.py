from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_merchant, require_admin
from app.core.database import get_db
from app.merchant.merchant_model import Merchant
from app.tenant_balance import tenant_balance_service
from app.tenant_balance.tenant_balance_schema import TenantBalanceOut

router = APIRouter(prefix="/tenant-balance", tags=["Tenant Balance"])


@router.get("/me", response_model=TenantBalanceOut,
            summary="[Merchant] Lihat saldo sendiri")
def get_my_balance(
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Merchant lihat saldo, pending, dan total yang sudah dicairkan."""
    return tenant_balance_service.get_or_create_balance(db, current_merchant.id)


@router.get("/{merchant_id}", response_model=TenantBalanceOut,
            summary="[Admin] Lihat saldo merchant tertentu")
def get_balance_by_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return tenant_balance_service.get_or_create_balance(db, merchant_id)