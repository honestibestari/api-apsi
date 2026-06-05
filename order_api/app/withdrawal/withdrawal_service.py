from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.withdrawal.withdrawal_model import Withdrawal, WithdrawalStatus


def list_withdrawals(
    db: Session,
    merchant_id: Optional[int] = None,
    status: Optional[WithdrawalStatus] = None,
    offset: int = 0,
    limit: int = 20,
) -> List[Withdrawal]:
    query = db.query(Withdrawal).order_by(Withdrawal.created_at.desc())
    if merchant_id:
        query = query.filter(Withdrawal.merchant_id == merchant_id)
    if status:
        query = query.filter(Withdrawal.status == status)
    return query.offset(offset).limit(limit).all()


def create_withdrawal(db: Session, merchant_id: int, data) -> Withdrawal:
    w = Withdrawal(
        merchant_id    = merchant_id,
        amount         = data.amount,
        status         = WithdrawalStatus.PENDING,
        bank           = data.bank,
        account_number = data.account_number,
        account_name   = data.account_name,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def approve_withdrawal(db: Session, withdrawal_id: int) -> Withdrawal:
    w = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "Withdrawal tidak ditemukan")
    if w.status != WithdrawalStatus.PENDING:
        raise HTTPException(400, f"Withdrawal sudah berstatus '{w.status}'")
    w.status       = WithdrawalStatus.APPROVED
    w.processed_at = datetime.now()
    w.note         = "Disetujui oleh admin"
    db.commit()
    db.refresh(w)
    return w


def reject_withdrawal(db: Session, withdrawal_id: int, note: Optional[str] = None) -> Withdrawal:
    w = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "Withdrawal tidak ditemukan")
    if w.status != WithdrawalStatus.PENDING:
        raise HTTPException(400, f"Withdrawal sudah berstatus '{w.status}'")
    w.status       = WithdrawalStatus.REJECTED
    w.processed_at = datetime.now()
    w.note         = note or "Ditolak oleh admin"
    db.commit()
    db.refresh(w)
    return w