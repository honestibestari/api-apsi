from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.merchant.merchant_model import Merchant
from app.merchant_order.merchant_order_model import Notification, NotifikasiTipe
from app.withdrawal.withdrawal_model import Withdrawal, WithdrawalStatus
from app.withdrawal.withdrawal_schema import WithdrawalSummary, WithdrawalStatusSummary


# ── Helper notifikasi ─────────────────────────────────────────────────────────

def _kirim_notif_pencairan(
    db: Session,
    merchant_id: int,
    judul: str,
    pesan: str,
) -> None:
    notif = Notification(
        merchant_id       = merchant_id,
        merchant_order_id = None,
        tipe              = NotifikasiTipe.PENCAIRAN,
        judul             = judul,
        pesan             = pesan,
    )
    db.add(notif)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def list_withdrawals(
    db: Session,
    merchant_id: Optional[int] = None,
    status: Optional[WithdrawalStatus] = None,
    offset: int = 0,
    limit: int = 20,
) -> List[Withdrawal]:
    query = (
        db.query(Withdrawal)
        .options(joinedload(Withdrawal.merchant))
        .order_by(Withdrawal.requested_at.desc())
    )
    if merchant_id:
        query = query.filter(Withdrawal.merchant_id == merchant_id)
    if status:
        query = query.filter(Withdrawal.status == status)
    return query.offset(offset).limit(limit).all()


def get_summary(db: Session) -> WithdrawalSummary:
    rows = (
        db.query(
            Withdrawal.status,
            func.count(Withdrawal.id).label("count"),
            func.coalesce(func.sum(Withdrawal.amount), 0).label("total_amount"),
        )
        .group_by(Withdrawal.status)
        .all()
    )
    result = {
        s: WithdrawalStatusSummary(count=0, total_amount=0.0)
        for s in ("pending", "approved", "rejected")
    }
    for row in rows:
        result[row.status] = WithdrawalStatusSummary(
            count=row.count, total_amount=float(row.total_amount)
        )
    return WithdrawalSummary(**result)


def _available_balance(merchant: Merchant) -> float:
    locked = sum(
        w.amount
        for w in merchant.withdrawals
        if w.status in (WithdrawalStatus.APPROVED, WithdrawalStatus.PENDING)
    )
    return merchant.balance - locked


def create_withdrawal(db: Session, merchant_id: int, data) -> Withdrawal:
    merchant = (
        db.query(Merchant)
        .options(
            joinedload(Merchant.withdrawals),
            joinedload(Merchant.merchant_orders),
        )
        .filter(Merchant.id == merchant_id)
        .first()
    )
    if not merchant:
        raise HTTPException(404, "Merchant tidak ditemukan")

    available = _available_balance(merchant)
    if data.amount > available:
        raise HTTPException(
            400,
            f"Saldo tidak cukup. Saldo tersedia: Rp {available:,.0f}",
        )

    w = Withdrawal(
        merchant_id    = merchant_id,
        amount         = data.amount,
        status         = WithdrawalStatus.PENDING,
        bank           = data.bank,
        account_number = data.account_number,
        account_name   = data.account_name,
    )
    db.add(w)

    # Notifikasi: pengajuan pencairan berhasil
    _kirim_notif_pencairan(
        db,
        merchant_id = merchant_id,
        judul       = "Pengajuan Pencairan Dikirim",
        pesan       = f"Pengajuan pencairan sebesar Rp {data.amount:,.0f} sedang diproses admin.",
    )

    db.commit()
    db.refresh(w)
    return w


def approve_withdrawal(
    db: Session, withdrawal_id: int, processed_by: Optional[int] = None
) -> Withdrawal:
    w = (
        db.query(Withdrawal)
        .options(joinedload(Withdrawal.merchant).joinedload(Merchant.withdrawals))
        .options(joinedload(Withdrawal.merchant).joinedload(Merchant.merchant_orders))
        .filter(Withdrawal.id == withdrawal_id)
        .with_for_update()
        .first()
    )
    if not w:
        raise HTTPException(404, "Withdrawal tidak ditemukan")
    if w.status != WithdrawalStatus.PENDING:
        raise HTTPException(400, f"Withdrawal sudah berstatus '{w.status}'")

    available = _available_balance(w.merchant) + w.amount
    if w.amount > available:
        raise HTTPException(
            400,
            f"Saldo merchant tidak mencukupi saat approve. Tersedia: Rp {available:,.0f}",
        )

    w.status       = WithdrawalStatus.APPROVED
    w.processed_at = datetime.now()
    w.processed_by = processed_by
    w.note         = "Disetujui oleh admin"

    # Notifikasi: pencairan disetujui
    _kirim_notif_pencairan(
        db,
        merchant_id = w.merchant_id,
        judul       = "Pencairan Disetujui ✓",
        pesan       = f"Pencairan sebesar Rp {w.amount:,.0f} telah disetujui dan sedang diproses ke rekening Anda.",
    )

    db.commit()
    db.refresh(w)
    return w


def reject_withdrawal(
    db: Session,
    withdrawal_id: int,
    note: Optional[str] = None,
    processed_by: Optional[int] = None,
) -> Withdrawal:
    w = (
        db.query(Withdrawal)
        .filter(Withdrawal.id == withdrawal_id)
        .with_for_update()
        .first()
    )
    if not w:
        raise HTTPException(404, "Withdrawal tidak ditemukan")
    if w.status != WithdrawalStatus.PENDING:
        raise HTTPException(400, f"Withdrawal sudah berstatus '{w.status}'")

    w.status       = WithdrawalStatus.REJECTED
    w.processed_at = datetime.now()
    w.processed_by = processed_by
    w.note         = note or "Ditolak oleh admin"

    # Notifikasi: pencairan ditolak
    _kirim_notif_pencairan(
        db,
        merchant_id = w.merchant_id,
        judul       = "Pencairan Ditolak",
        pesan       = f"Pencairan sebesar Rp {w.amount:,.0f} ditolak. Alasan: {w.note}",
    )

    db.commit()
    db.refresh(w)
    return w