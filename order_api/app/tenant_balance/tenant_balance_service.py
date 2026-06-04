from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.tenant_balance.tenant_balance_model import TenantBalance


def get_or_create_balance(db: Session, merchant_id: int) -> TenantBalance:
    """Ambil saldo tenant, buat baru jika belum ada."""
    balance = db.query(TenantBalance).filter(
        TenantBalance.id_tenant == merchant_id
    ).first()
    if not balance:
        balance = TenantBalance(id_tenant=merchant_id)
        db.add(balance)
        db.commit()
        db.refresh(balance)
    return balance


def get_balance_or_404(db: Session, merchant_id: int) -> TenantBalance:
    balance = db.query(TenantBalance).filter(
        TenantBalance.id_tenant == merchant_id
    ).first()
    if not balance:
        raise HTTPException(404, "Saldo tenant tidak ditemukan")
    return balance


def update_balance(
    db: Session,
    merchant_id: int,
    tambah_saldo: float = 0.0,
    tambah_pending: float = 0.0,
    tambah_dicairkan: float = 0.0,
) -> TenantBalance:
    """Update saldo tenant — dipanggil saat order selesai atau withdrawal disetujui."""
    balance = get_or_create_balance(db, merchant_id)
    balance.total_saldo     += tambah_saldo
    balance.total_pending   += tambah_pending
    balance.total_dicairkan += tambah_dicairkan
    db.commit()
    db.refresh(balance)
    return balance