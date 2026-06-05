from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.customer_order.customer_order_model import CustomerOrder, CustomerOrderStatus
from app.merchant.merchant_model import Merchant, MerchantStatus
from app.merchant_order.merchant_order_model import MerchantOrder
from app.customer.customer_model import Customer
from app.withdrawal.withdrawal_model import Withdrawal

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Dashboard ringkasan ───────────────────────────────────────────────────────

@router.get("/dashboard", summary="Ringkasan statistik sistem")
def dashboard(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Statistik keseluruhan sistem untuk halaman dashboard admin."""
    from sqlalchemy import func

    total_merchant  = db.query(func.count(Merchant.id)).scalar()
    aktif_merchant  = db.query(func.count(Merchant.id)).filter(Merchant.status == MerchantStatus.ACTIVE).scalar()
    total_customer  = db.query(func.count(Customer.id)).scalar()
    total_order     = db.query(func.count(CustomerOrder.id)).scalar()
    total_pendapatan = db.query(func.sum(CustomerOrder.total_harga)).filter(
        CustomerOrder.status == CustomerOrderStatus.DONE
    ).scalar() or 0.0

    return {
        "total_merchant":   total_merchant,
        "merchant_aktif":   aktif_merchant,
        "total_customer":   total_customer,
        "total_order":      total_order,
        "total_pendapatan": total_pendapatan,
    }


# ── Pantau merchant ───────────────────────────────────────────────────────────

@router.get("/merchants", summary="List semua merchant")
def list_merchants(
    status: Optional[MerchantStatus] = Query(None),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    query = db.query(Merchant).order_by(Merchant.created_at.desc())
    if status:
        query = query.filter(Merchant.status == status)
    return query.offset(offset).limit(limit).all()


@router.put("/merchants/{merchant_id}/status", summary="Ubah status merchant")
def update_merchant_status(
    merchant_id: int,
    status: MerchantStatus,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Admin bisa aktifkan, suspend, atau nonaktifkan merchant."""
    from fastapi import HTTPException
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(404, "Merchant tidak ditemukan")
    merchant.status = status
    db.commit()
    db.refresh(merchant)
    return {"message": f"Status merchant '{merchant.nama}' diubah ke {status}", "id": merchant_id}


# ── Pantau customer ───────────────────────────────────────────────────────────

@router.get("/customers", summary="List semua customer")
def list_customers(
    search: Optional[str] = Query(None, description="Cari nama/email/phone"),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    query = db.query(Customer).order_by(Customer.created_at.desc())
    if search:
        like = f"%{search}%"
        query = query.filter(
            Customer.nama.ilike(like) |
            Customer.email.ilike(like) |
            Customer.phone.ilike(like)
        )
    return query.offset(offset).limit(limit).all()


# ── Pantau semua order ────────────────────────────────────────────────────────

@router.get("/orders", summary="List semua customer order")
def list_all_orders(
    status: Optional[CustomerOrderStatus] = Query(None),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    from sqlalchemy.orm import joinedload
    query = (
        db.query(CustomerOrder)
        .options(joinedload(CustomerOrder.customer))
        .order_by(CustomerOrder.created_at.desc())
    )
    if status:
        query = query.filter(CustomerOrder.status == status)
    return query.offset(offset).limit(limit).all()


# ── Pantau keuangan (withdrawal) ──────────────────────────────────────────────

@router.get("/withdrawals", summary="List semua penarikan dana")
def list_withdrawals(
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    return (
        db.query(Withdrawal)
        .order_by(Withdrawal.requested_at.desc())
        .offset(offset).limit(limit).all()
    )


@router.put("/withdrawals/{withdrawal_id}/approve", summary="Setujui penarikan dana")
def approve_withdrawal(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    from fastapi import HTTPException
    from app.withdrawal.withdrawal_model import WithdrawalStatus
    from datetime import datetime

    w = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "Withdrawal tidak ditemukan")
    if w.status != WithdrawalStatus.PENDING:
        raise HTTPException(400, f"Withdrawal sudah berstatus {w.status}")
    w.status = WithdrawalStatus.APPROVED
    w.processed_at = datetime.now()
    w.note = "Disetujui oleh admin"
    db.commit()
    return {"message": "Withdrawal disetujui", "id": withdrawal_id}


@router.put("/withdrawals/{withdrawal_id}/reject", summary="Tolak penarikan dana")
def reject_withdrawal(
    withdrawal_id: int,
    note: Optional[str] = Query(None, description="Alasan penolakan"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    from fastapi import HTTPException
    from app.withdrawal.withdrawal_model import WithdrawalStatus
    from datetime import datetime

    w = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "Withdrawal tidak ditemukan")
    if w.status != WithdrawalStatus.PENDING:
        raise HTTPException(400, f"Withdrawal sudah berstatus {w.status}")
    w.status = WithdrawalStatus.REJECTED
    w.processed_at = datetime.now()
    w.note = note or "Ditolak oleh admin"
    db.commit()
    return {"message": "Withdrawal ditolak", "id": withdrawal_id}