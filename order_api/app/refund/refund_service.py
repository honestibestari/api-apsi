from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.refund.refund_model import Refund, StatusRefund
from app.refund.refund_schema import RefundCreate


# Metode refund yang didukung — hanya e-wallet.
ALLOWED_EWALLETS = ["GoPay", "OVO", "DANA", "ShopeePay"]


def get_refund_or_404(db: Session, refund_id: int) -> Refund:
    r = db.query(Refund).filter(Refund.id == refund_id).first()
    if not r:
        raise HTTPException(404, "Refund tidak ditemukan")
    return r


def get_refund_by_order(db: Session, order_id: int) -> Optional[Refund]:
    """Refund terbaru untuk sebuah customer order (atau None)."""
    return (
        db.query(Refund)
        .filter(Refund.id_pesanan == order_id)
        .order_by(Refund.timestamp.desc())
        .first()
    )


def process_refund_choice(
    db: Session, order_id: int, metode_refund: str, nomor_tujuan: str
) -> Refund:
    """Customer memilih metode + nomor e-wallet tujuan refund.

    Mode dummy   : transfer di-bypass → status langsung DISETUJUI (demo).
    Mode gateway : uang ASLI — status tetap PENDING; pengelola mentransfer
    manual ke e-wallet tujuan lalu menandai selesai via
    PUT /refunds/{id}/status (admin). Customer boleh mengoreksi metode/nomor
    selama masih PENDING.
    """
    refund = get_refund_by_order(db, order_id)
    if not refund:
        raise HTTPException(404, "Refund untuk pesanan ini tidak ditemukan")
    if refund.status != StatusRefund.PENDING:
        raise HTTPException(400, "Refund sudah diproses sebelumnya")
    if metode_refund not in ALLOWED_EWALLETS:
        raise HTTPException(400, f"Metode refund harus salah satu e-wallet: {', '.join(ALLOWED_EWALLETS)}")
    if not (nomor_tujuan or "").strip():
        raise HTTPException(400, "Nomor tujuan e-wallet wajib diisi")

    refund.metode_refund = metode_refund
    refund.nomor_tujuan = nomor_tujuan.strip()
    if settings.payment_gateway.lower() == "dummy":
        refund.status = StatusRefund.DISETUJUI  # demo: transfer di-bypass
    db.commit()
    db.refresh(refund)
    return refund


def list_refunds(db: Session, id_pesanan: Optional[int] = None) -> List[Refund]:
    query = db.query(Refund).order_by(Refund.timestamp.desc())
    if id_pesanan:
        query = query.filter(Refund.id_pesanan == id_pesanan)
    return query.all()


def create_refund(db: Session, data: RefundCreate) -> Refund:
    # Cek apakah sudah ada refund pending/disetujui untuk pesanan ini
    existing = db.query(Refund).filter(
        Refund.id_pesanan == data.id_pesanan,
        Refund.status.in_([StatusRefund.PENDING, StatusRefund.DISETUJUI])
    ).first()
    if existing:
        raise HTTPException(400, "Refund untuk pesanan ini sudah diajukan")

    refund = Refund(
        id_pesanan    = data.id_pesanan,
        nominal       = data.nominal,
        metode_refund = data.metode_refund,
        nomor_tujuan  = data.nomor_tujuan,
        status        = StatusRefund.PENDING,
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund


def update_refund_status(db: Session, refund_id: int, status: StatusRefund) -> Refund:
    refund = get_refund_or_404(db, refund_id)
    if refund.status != StatusRefund.PENDING:
        raise HTTPException(400, f"Refund sudah berstatus '{refund.status}', tidak bisa diubah")
    refund.status = status
    db.commit()
    db.refresh(refund)
    return refund