from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_merchant, require_admin
from app.core.database import get_db
from app.merchant.merchant_model import Merchant
from app.withdrawal import withdrawal_service
from app.withdrawal.withdrawal_model import WithdrawalStatus
from app.withdrawal.withdrawal_schema import WithdrawalCreate, WithdrawalOut, WithdrawalSummary

router = APIRouter(prefix="/withdrawals", tags=["Withdrawals"])


@router.get("/summary", response_model=WithdrawalSummary, summary="[Admin] Ringkasan statistik withdrawal")
def withdrawal_summary(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return withdrawal_service.get_summary(db)


@router.get("", response_model=List[WithdrawalOut], summary="[Admin] List semua withdrawal")
def list_withdrawals(
    merchant_id: Optional[int]              = Query(None),
    status:      Optional[WithdrawalStatus] = Query(None),
    offset:      int = Query(0, ge=0),
    limit:       int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return withdrawal_service.list_withdrawals(
        db, merchant_id=merchant_id, status=status, offset=offset, limit=limit
    )


@router.get("/me", response_model=List[WithdrawalOut],
            summary="[Merchant] List withdrawal milik sendiri")
def list_my_withdrawals(
    status: Optional[WithdrawalStatus] = Query(None),
    offset: int = Query(0, ge=0),
    limit:  int = Query(20, ge=1, le=100),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return withdrawal_service.list_withdrawals(
        db, merchant_id=current_merchant.id, status=status, offset=offset, limit=limit
    )


@router.post("", response_model=WithdrawalOut, status_code=status.HTTP_201_CREATED,
             summary="[Merchant] Ajukan penarikan dana")
def create_withdrawal(
    data: WithdrawalCreate,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return withdrawal_service.create_withdrawal(db, current_merchant.id, data)


@router.put("/{withdrawal_id}/approve", response_model=WithdrawalOut,
            summary="[Admin] Setujui withdrawal")
def approve_withdrawal(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return withdrawal_service.approve_withdrawal(
        db, withdrawal_id, processed_by=current_admin.id
    )


@router.put("/{withdrawal_id}/reject", response_model=WithdrawalOut,
            summary="[Admin] Tolak withdrawal")
def reject_withdrawal(
    withdrawal_id: int,
    note: Optional[str] = Query(None, description="Alasan penolakan"),
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return withdrawal_service.reject_withdrawal(
        db, withdrawal_id, note=note, processed_by=current_admin.id
    )
