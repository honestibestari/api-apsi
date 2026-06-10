from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.payment import payment_service
from app.payment.payment_model import StatusPembayaran
from app.payment.payment_schema import (
    ChargeRequest,
    ChargeResponse,
    PaymentCreate,
    PaymentOut,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── Dummy gateway flow (siap di-swap ke Midtrans/Flip) ──────────────────────

@router.post("/charge", response_model=ChargeResponse, status_code=status.HTTP_201_CREATED,
             summary="Buat transaksi pembayaran (dummy gateway)")
def charge(data: ChargeRequest, db: Session = Depends(get_db)):
    return payment_service.charge(db, data.id_pesanan, data.metode_pembayaran_id)


@router.get("/{payment_id}/status", response_model=ChargeResponse,
            summary="Status pembayaran (untuk polling FE)")
def charge_status(payment_id: int, db: Session = Depends(get_db)):
    return payment_service.get_charge_status(db, payment_id)


@router.post("/{payment_id}/simulate-paid", response_model=ChargeResponse,
             summary="Tandai LUNAS (pengganti webhook gateway, fase dummy)")
def simulate_paid(payment_id: int, db: Session = Depends(get_db)):
    return payment_service.simulate_paid(db, payment_id)


@router.get("", response_model=List[PaymentOut], summary="List pembayaran")
def list_payments(
    id_pesanan: Optional[int] = Query(None, description="Filter per pesanan"),
    db: Session = Depends(get_db),
):
    return payment_service.list_payments(db, id_pesanan=id_pesanan)


@router.get("/{payment_id}", response_model=PaymentOut, summary="Detail pembayaran")
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    return payment_service.get_payment_or_404(db, payment_id)


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED,
             summary="Buat pembayaran baru")
def create_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    return payment_service.create_payment(db, data)


@router.put("/{payment_id}/status", response_model=PaymentOut,
            summary="Update status pembayaran")
def update_status(
    payment_id: int,
    status: StatusPembayaran = Query(..., description="pending | lunas | gagal | refunded"),
    db: Session = Depends(get_db),
):
    return payment_service.update_payment_status(db, payment_id, status)