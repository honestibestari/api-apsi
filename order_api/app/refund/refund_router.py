from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core import idhash
from app.core.auth import require_admin
from app.core.database import get_db
from app.refund import refund_service
from app.refund.refund_model import StatusRefund
from app.refund.refund_schema import RefundCreate, RefundOut, RefundProcess

router = APIRouter(prefix="/refunds", tags=["Refunds"])

_ORDER_SALT = "customer_order"


def _order_id_from_hash(order_hash: str) -> int:
    oid = idhash.decode(_ORDER_SALT, order_hash)
    if oid is None:
        raise HTTPException(404, "Pesanan tidak ditemukan")
    return oid


# ── Akses publik via HASH order (untuk link refund di email) ────────────────────

@router.get("/order/{order_hash}", response_model=RefundOut,
            summary="[Customer] Detail refund untuk sebuah order (via hash)")
def get_refund_by_order_hash(order_hash: str, db: Session = Depends(get_db)):
    refund = refund_service.get_refund_by_order(db, _order_id_from_hash(order_hash))
    if not refund:
        raise HTTPException(404, "Refund tidak ditemukan untuk pesanan ini")
    return refund


@router.get("/ewallets", summary="[Customer] Daftar e-wallet yang didukung untuk refund")
def list_ewallets():
    return refund_service.ALLOWED_EWALLETS


@router.post("/order/{order_hash}/process", response_model=RefundOut,
             summary="[Customer] Pilih metode e-wallet & selesaikan refund (bypass transfer)")
def process_refund(order_hash: str, data: RefundProcess, db: Session = Depends(get_db)):
    return refund_service.process_refund_choice(
        db, _order_id_from_hash(order_hash), data.metode_refund, data.nomor_tujuan
    )


@router.get("", response_model=List[RefundOut], summary="List refund (admin)")
def list_refunds(
    id_pesanan: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return refund_service.list_refunds(db, id_pesanan=id_pesanan)


@router.get("/{refund_id}", response_model=RefundOut, summary="Detail refund")
def get_refund(refund_id: int, db: Session = Depends(get_db)):
    return refund_service.get_refund_or_404(db, refund_id)


@router.post("", response_model=RefundOut, status_code=status.HTTP_201_CREATED,
             summary="Ajukan refund (customer)")
def create_refund(data: RefundCreate, db: Session = Depends(get_db)):
    return refund_service.create_refund(db, data)


@router.put("/{refund_id}/status", response_model=RefundOut,
            summary="Setujui atau tolak refund (admin)")
def update_refund_status(
    refund_id: int,
    status: StatusRefund = Query(..., description="disetujui | ditolak"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return refund_service.update_refund_status(db, refund_id, status)