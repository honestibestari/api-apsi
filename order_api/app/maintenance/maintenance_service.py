"""Sweep maintenance siklus order.

Menggerakkan semua timeout siklus order tanpa bergantung pada polling FE:
  • 'verifying' (belum dibayar) basi      → dibatalkan + stok dikembalikan
  • 'terbuka' (menunggu merchant) basi    → dibatalkan + stok + refund parsial
  • 'waiting_confirmation' tak dikonfirmasi → otomatis 'done'
  • 'diproses' lewat SLA                    → notifikasi 'terlambat' (sekali)

Dijalankan periodik oleh scheduler internal (main.py) DAN bisa dipicu manual
via POST /maintenance/sweep (untuk cron eksternal di lingkungan serverless).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import SessionLocal
from app.customer_order import customer_order_service as co_svc
from app.customer_order.customer_order_model import CustomerOrder, CustomerOrderStatus
from app.merchant_order.merchant_order_model import (
    MerchantOrder,
    MerchantOrderStatus,
    Notification,
    NotifikasiTipe,
    OrderItem,
)

_OVERDUE_JUDUL = "Pesanan terlambat"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _is_past(ref, secs: int) -> bool:
    ref = _aware(ref)
    if ref is None:
        return False
    return (_now() - ref).total_seconds() >= secs


# ── Tahap-tahap sweep ──────────────────────────────────────────────────────────

def _expire_unpaid_orders(db: Session) -> int:
    """Batalkan order 'verifying' yang melewati batas pembayaran; lepaskan stok."""
    secs = settings.customer_pay_timeout_seconds
    if secs <= 0:
        return 0
    orders = (
        db.query(CustomerOrder)
        .options(
            joinedload(CustomerOrder.merchant_orders)
            .joinedload(MerchantOrder.items)
            .joinedload(OrderItem.product)
        )
        .filter(CustomerOrder.status == CustomerOrderStatus.VERIFYING)
        .all()
    )
    n = 0
    for order in orders:
        if not _is_past(order.created_at, secs):
            continue
        for mo in order.merchant_orders:
            # Belum dibayar → tanpa refund.
            co_svc.cancel_merchant_order(db, mo, create_refund=False)
        order.status = CustomerOrderStatus.CANCELLED
        n += 1
    return n


def _cancel_stale_terbuka(db: Session) -> int:
    """Batalkan merchant order 'terbuka' (sudah dibayar) yang tak direspons merchant."""
    secs = settings.merchant_decide_timeout_seconds
    if secs <= 0:
        return 0
    mos = (
        db.query(MerchantOrder)
        .options(
            joinedload(MerchantOrder.items).joinedload(OrderItem.product),
            joinedload(MerchantOrder.customer_order),
        )
        .filter(MerchantOrder.status == MerchantOrderStatus.TERBUKA)
        .all()
    )
    n = 0
    for mo in mos:
        if not _is_past(mo.updated_at or mo.created_at, secs):
            continue
        co_svc.cancel_merchant_order(db, mo)  # sudah dibayar → refund parsial
        db.add(Notification(
            merchant_id       = mo.merchant_id,
            merchant_order_id = mo.id,
            tipe              = NotifikasiTipe.ORDER_DIBATALKAN,
            judul             = "Pesanan dibatalkan otomatis",
            pesan             = f"{mo.order_code} dibatalkan karena tidak direspons tepat waktu.",
        ))
        if mo.customer_order:
            co_svc.sync_customer_order_status(mo.customer_order)
        n += 1
    return n


def _autocomplete_confirmations(db: Session) -> int:
    """Auto-'done' order 'waiting_confirmation' yang tak dikonfirmasi customer."""
    secs = settings.customer_confirm_timeout_seconds
    if secs <= 0:
        return 0
    orders = (
        db.query(CustomerOrder)
        .filter(CustomerOrder.status == CustomerOrderStatus.WAITING_CONFIRMATION)
        .all()
    )
    n = 0
    for order in orders:
        if not _is_past(order.updated_at or order.created_at, secs):
            continue
        order.status = CustomerOrderStatus.DONE
        n += 1
    return n


def _flag_overdue_prep(db: Session) -> int:
    """Kirim pengingat (sekali) untuk pesanan 'diproses' yang melewati SLA."""
    secs = settings.merchant_prep_timeout_seconds
    if secs <= 0:
        return 0
    mos = (
        db.query(MerchantOrder)
        .filter(MerchantOrder.status == MerchantOrderStatus.DIPROSES)
        .all()
    )
    n = 0
    for mo in mos:
        if not _is_past(mo.updated_at or mo.created_at, secs):
            continue
        # Hindari spam: lewati bila pengingat 'terlambat' untuk order ini sudah ada.
        already = (
            db.query(Notification)
            .filter(
                Notification.merchant_order_id == mo.id,
                Notification.judul == _OVERDUE_JUDUL,
            )
            .first()
        )
        if already:
            continue
        db.add(Notification(
            merchant_id       = mo.merchant_id,
            merchant_order_id = mo.id,
            tipe              = NotifikasiTipe.STATUS_BERUBAH,
            judul             = _OVERDUE_JUDUL,
            pesan             = f"{mo.order_code} melewati batas waktu penyelesaian. Segera selesaikan.",
        ))
        n += 1
    return n


# ── Entry point ─────────────────────────────────────────────────────────────────

def run_maintenance_sweep(db: Session) -> dict:
    """Jalankan semua tahap sweep dalam satu transaksi. Return ringkasan jumlah."""
    result = {
        "unpaid_cancelled":     _expire_unpaid_orders(db),
        "terbuka_cancelled":    _cancel_stale_terbuka(db),
        "auto_confirmed":       _autocomplete_confirmations(db),
        "prep_overdue_flagged": _flag_overdue_prep(db),
    }
    db.commit()
    return result


def run_sweep_with_session() -> dict:
    """Bungkus run_maintenance_sweep dengan session sendiri (untuk scheduler)."""
    db = SessionLocal()
    try:
        return run_maintenance_sweep(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
