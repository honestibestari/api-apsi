from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.payment import tripay_client
from app.payment_method.payment_method_model import PaymentMethod
from app.payment_method.payment_method_schema import (
    PaymentMethodCreate,
    PaymentMethodOut,
    PaymentMethodUpdate,
    TripaySyncResult,
)

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])


@router.post("/sync-tripay", response_model=TripaySyncResult,
             summary="Sinkronkan metode pembayaran dari channel Tripay (admin)")
def sync_tripay(db: Session = Depends(get_db), _=Depends(require_admin)):
    """Tarik daftar channel dari akun Tripay lalu upsert ke payment_methods.

    Aturan:
      • Channel baru → dibuat NONAKTIF (admin tinggal mengaktifkan).
      • Channel yang sudah ada (match tripay_code, atau nama untuk adopsi baris
        lama) → nama & struktur fee di-update mengikuti Tripay.
      • Channel yang nonaktif/hilang di Tripay → metode ikut dinonaktifkan.
      • Metode lokal tanpa tripay_code (mis. Tunai) tidak disentuh.
    Bisa dijalankan meski PAYMENT_GATEWAY masih dummy — cukup kredensial terisi,
    jadi katalog bisa disiapkan sebelum gateway diaktifkan.
    """
    if not tripay_client.is_configured():
        raise HTTPException(503, "Kredensial Tripay belum diisi di .env backend")

    channels = tripay_client.get_payment_channels()  # 502 bila Tripay tak bisa dihubungi

    rows = db.query(PaymentMethod).all()
    by_code = {r.tripay_code: r for r in rows if r.tripay_code}
    by_name = {r.nama_metode.lower(): r for r in rows}

    added = updated = deactivated = 0
    seen_codes = set()
    for ch in channels:
        code = (ch.get("code") or "").upper()
        name = (ch.get("name") or code).strip()
        if not code:
            continue
        seen_codes.add(code)
        fee_cust = ch.get("fee_customer") or {}
        fee_flat = float(fee_cust.get("flat") or 0)
        fee_percent = float(fee_cust.get("percent") or 0)
        ch_active = bool(ch.get("active", True))

        row = by_code.get(code) or by_name.get(name.lower())
        if row is None:
            row = PaymentMethod(nama_metode=name, tripay_code=code,
                                is_active=False,  # admin yang memutuskan aktif
                                fee_flat=fee_flat, fee_percent=fee_percent)
            db.add(row)
            added += 1
        else:
            row.tripay_code = code
            # Ikuti nama channel Tripay, kecuali nama itu sudah dipakai baris lain.
            pemilik_nama = by_name.get(name.lower())
            if pemilik_nama is None or pemilik_nama is row:
                row.nama_metode = name
            row.fee_flat = fee_flat
            row.fee_percent = fee_percent
            if not ch_active and row.is_active:
                row.is_active = False
                deactivated += 1
            updated += 1
        by_name[name.lower()] = row

    # Channel yang hilang dari akun Tripay → nonaktifkan metode terkait.
    for code, row in by_code.items():
        if code not in seen_codes and row.is_active:
            row.is_active = False
            deactivated += 1

    db.commit()
    methods = db.query(PaymentMethod).order_by(PaymentMethod.id).all()
    return TripaySyncResult(added=added, updated=updated,
                            deactivated=deactivated, methods=methods)


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
    pm = PaymentMethod(
        nama_metode=data.nama_metode,
        tripay_code=(data.tripay_code or "").strip().upper() or None,
    )
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
    if data.tripay_code is not None:
        # "" (string kosong) = lepas kode; selain itu dinormalkan ke uppercase.
        pm.tripay_code = data.tripay_code.strip().upper() or None

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