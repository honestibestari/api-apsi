from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core import idhash
from app.core.auth import require_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.email import build_order_created_html, send_email
from app.customer_order import customer_order_service
from app.customer_order.customer_order_model import CustomerOrderStatus
from app.customer_order.customer_order_schema import (
    CustomerOrderCreate,
    CustomerOrderOut,
    CustomerOrderSummary,
)

router = APIRouter(prefix="/customer-orders", tags=["Customer Orders"])

_HASH_SALT = "customer_order"


def _order_id_from_hash(order_hash: str) -> int:
    """Decode hash publik → id, atau 404 bila tidak valid/dipalsukan."""
    oid = idhash.decode(_HASH_SALT, order_hash)
    if oid is None:
        raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan")
    return oid


@router.post(
    "",
    response_model=CustomerOrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Customer] Buat pesanan (otomatis dipecah ke merchant order)",
)
def create_customer_order(
    data: CustomerOrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Buat satu customer order. Item lintas-tenant dipecah otomatis menjadi
    beberapa merchant order. Status awal: verifying.

    Setelah order dibuat, kirim email konfirmasi ke pelanggan (berisi tombol untuk
    membuka kembali pesanannya). Pengiriman dijadwalkan sebagai background task —
    tidak memperlambat respons & tidak menggagalkan order bila kirim email gagal.
    """
    order = customer_order_service.create_customer_order(db, data)

    # Bangun HTML SAAT request (order masih ter-attach ke session), lalu kirim
    # via background task (hanya HTTP ke Gmail API, tanpa akses DB).
    try:
        to = order.customer.email if order.customer else None
        if to:
            view_url = f"{settings.frontend_url.rstrip('/')}/order/{order.hash}"
            html = build_order_created_html(order, view_url)
            background_tasks.add_task(
                send_email, to, f"Pesanan {order.order_code} diterima — Teras LA", html
            )
    except Exception as exc:  # noqa: BLE001 — email tidak boleh menggagalkan order
        print(f"[email] gagal menjadwalkan email order: {exc}")

    return order


@router.get(
    "",
    response_model=List[CustomerOrderSummary],
    summary="[Admin] List semua customer order",
)
def list_customer_orders(
    status: Optional[CustomerOrderStatus] = Query(None, description="Filter status customer order"),
    customer_id: Optional[int] = Query(None, description="Filter order milik satu customer"),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return customer_order_service.list_customer_orders(
        db, status=status, customer_id=customer_id, offset=offset, limit=limit
    )


# ── Akses publik via HASH (link email / halaman ringkasan tanpa login) ──────────

@router.get(
    "/h/{order_hash}",
    response_model=CustomerOrderOut,
    summary="[Customer] Detail order via hash (opaque, tak bisa ditebak)",
)
def get_customer_order_by_hash(order_hash: str, db: Session = Depends(get_db)):
    return customer_order_service.get_customer_order_or_404(db, _order_id_from_hash(order_hash))


@router.post(
    "/h/{order_hash}/confirm",
    response_model=CustomerOrderOut,
    summary="[Customer] Konfirmasi pesanan selesai via hash (waiting_confirmation → done)",
)
def confirm_order_by_hash(order_hash: str, db: Session = Depends(get_db)):
    return customer_order_service.confirm_order(db, _order_id_from_hash(order_hash))


# ── Akses by-id: ADMIN ONLY (mengandung PII pelanggan) ──────────────────────────

@router.get(
    "/{order_id}",
    response_model=CustomerOrderOut,
    summary="[Admin] Detail customer order by id (struk multi-tenant)",
)
def get_customer_order(order_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    return customer_order_service.get_customer_order_or_404(db, order_id)
