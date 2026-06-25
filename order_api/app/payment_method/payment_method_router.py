from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.payment_method.payment_method_model import PaymentMethod
from app.payment_method.payment_method_schema import (
    PaymentMethodCreate,
    PaymentMethodOut,
    PaymentMethodUpdate,
)

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])


@router.get("", response_model=List[PaymentMethodOut], summary="List metode pembayaran")
def list_payment_methods(db: Session = Depends(get_db)):
    """Bisa diakses semua orang — customer perlu lihat ini saat checkout."""
    return db.query(PaymentMethod).all()


@router.post("", response_model=PaymentMethodOut, status_code=status.HTTP_201_CREATED,
             summary="Tambah metode pembayaran (admin)")
def create_payment_method(
    data: PaymentMethodCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    existing = db.query(PaymentMethod).filter(
        PaymentMethod.nama_metode == data.nama_metode
    ).first()
    if existing:
        raise HTTPException(409, f"Metode '{data.nama_metode}' sudah ada")
    pm = PaymentMethod(nama_metode=data.nama_metode)
    db.add(pm)
    db.commit()
    db.refresh(pm)
    return pm


@router.patch("/{pm_id}", response_model=PaymentMethodOut,
              summary="Update metode pembayaran — toggle aktif / ubah nama (admin)")
def update_payment_method(
    pm_id: int,
    data: PaymentMethodUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    pm = db.query(PaymentMethod).filter(PaymentMethod.id == pm_id).first()
    if not pm:
        raise HTTPException(404, "Metode pembayaran tidak ditemukan")

    if data.nama_metode is not None:
        nama = data.nama_metode.strip()
        if not nama:
            raise HTTPException(422, "Nama metode tidak boleh kosong")
        bentrok = db.query(PaymentMethod).filter(
            PaymentMethod.nama_metode == nama,
            PaymentMethod.id != pm_id,
        ).first()
        if bentrok:
            raise HTTPException(409, f"Metode '{nama}' sudah ada")
        pm.nama_metode = nama
    if data.is_active is not None:
        pm.is_active = data.is_active

    db.commit()
    db.refresh(pm)
    return pm


@router.delete("/{pm_id}", summary="Hapus metode pembayaran (admin)")
def delete_payment_method(
    pm_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    pm = db.query(PaymentMethod).filter(PaymentMethod.id == pm_id).first()
    if not pm:
        raise HTTPException(404, "Metode pembayaran tidak ditemukan")
    db.delete(pm)
    db.commit()
    return {"message": f"Metode '{pm.nama_metode}' berhasil dihapus"}