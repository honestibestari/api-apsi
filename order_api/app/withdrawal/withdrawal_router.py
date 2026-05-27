from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.withdrawal import withdrawal_service
from app.withdrawal.withdrawal_model import WithdrawalStatus
from app.withdrawal.withdrawal_schema import (
    WithdrawalCreate,
    WithdrawalOut,
    WithdrawalProcess,
)

router = APIRouter(prefix="/withdrawals", tags=["Withdrawals"])


@router.post(
    "",
    response_model=WithdrawalOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Merchant] Ajukan penarikan dana",
)
def create_withdrawal(data: WithdrawalCreate, db: Session = Depends(get_db)):
    return withdrawal_service.create_withdrawal(db, data)


@router.get(
    "",
    response_model=List[WithdrawalOut],
    summary="[Admin/Merchant] List penarikan",
)
def list_withdrawals(
    merchant_id: Optional[int]              = Query(None, description="Filter per merchant"),
    status:      Optional[WithdrawalStatus] = Query(None, description="pending | approved | rejected"),
    offset:      int                        = Query(0, ge=0),
    limit:       int                        = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return withdrawal_service.list_withdrawals(
        db, merchant_id=merchant_id, status=status, offset=offset, limit=limit
    )


@router.put(
    "/{withdrawal_id}/process",
    response_model=WithdrawalOut,
    summary="[Admin] Approve / reject penarikan",
)
def process_withdrawal(withdrawal_id: int, data: WithdrawalProcess, db: Session = Depends(get_db)):
    return withdrawal_service.process_withdrawal(db, withdrawal_id, data)
