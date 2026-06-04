from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.payment.payment_model import Payment, StatusPembayaran
from app.payment.payment_schema import PaymentCreate


def get_payment_or_404(db: Session, payment_id: int) -> Payment:
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(404, "Pembayaran tidak ditemukan")
    return p


def list_payments(db: Session, id_pesanan: Optional[int] = None) -> List[Payment]:
    query = db.query(Payment).order_by(Payment.timestamp.desc())
    if id_pesanan:
        query = query.filter(Payment.id_pesanan == id_pesanan)
    return query.all()


def create_payment(db: Session, data: PaymentCreate) -> Payment:
    # Cek apakah sudah ada payment LUNAS untuk pesanan ini
    existing = db.query(Payment).filter(
        Payment.id_pesanan == data.id_pesanan,
        Payment.status_pembayaran == StatusPembayaran.LUNAS
    ).first()
    if existing:
        raise HTTPException(400, "Pesanan ini sudah lunas")

    payment = Payment(
        id_pesanan        = data.id_pesanan,
        metode_pembayaran = data.metode_pembayaran,
        nominal           = data.nominal,
        qrcode_kode_url   = data.qrcode_kode_url,
        status_pembayaran = StatusPembayaran.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def update_payment_status(db: Session, payment_id: int, status: StatusPembayaran) -> Payment:
    payment = get_payment_or_404(db, payment_id)
    payment.status_pembayaran = status
    db.commit()
    db.refresh(payment)
    return payment