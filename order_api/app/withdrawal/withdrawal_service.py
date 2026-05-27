from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.merchant.merchant_service import get_merchant_or_404
from app.withdrawal.withdrawal_model import Withdrawal, WithdrawalStatus
from app.withdrawal.withdrawal_schema import WithdrawalCreate, WithdrawalProcess


def list_withdrawals(
    db: Session,
    merchant_id: Optional[int] = None,
    status: Optional[WithdrawalStatus] = None,
    offset: int = 0,
    limit: int = 50,
) -> List[Withdrawal]:
    query = db.query(Withdrawal).order_by(Withdrawal.requested_at.desc())
    if merchant_id is not None:
        query = query.filter(Withdrawal.merchant_id == merchant_id)
    if status:
        query = query.filter(Withdrawal.status == status)
    return query.offset(offset).limit(limit).all()


def get_withdrawal_or_404(db: Session, withdrawal_id: int) -> Withdrawal:
    w = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(status_code=404, detail=f"Withdrawal {withdrawal_id} tidak ditemukan")
    return w


def create_withdrawal(db: Session, data: WithdrawalCreate) -> Withdrawal:
    merchant = get_merchant_or_404(db, data.merchant_id)
    if data.amount > merchant.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Jumlah penarikan melebihi saldo tersedia ({merchant.balance})",
        )
    w = Withdrawal(
        merchant_id=data.merchant_id,
        amount=data.amount,
        bank=data.bank,
        account_number=data.account_number,
        account_name=data.account_name,
        status=WithdrawalStatus.PENDING,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def process_withdrawal(db: Session, withdrawal_id: int, data: WithdrawalProcess) -> Withdrawal:
    w = get_withdrawal_or_404(db, withdrawal_id)
    if w.status != WithdrawalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Withdrawal sudah diproses")
    w.status = data.status
    w.note = data.note or (
        "Disbursed successfully" if data.status == WithdrawalStatus.APPROVED else "Ditolak admin"
    )
    w.processed_at = datetime.now()
    db.commit()
    db.refresh(w)
    return w
