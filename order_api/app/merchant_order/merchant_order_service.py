from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.customer_order.customer_order_model import CustomerOrder
from app.customer_order.customer_order_service import (
    cancel_merchant_order,
    sync_customer_order_status,
)
from app.merchant_order.merchant_order_model import (
    MerchantOrder,
    MerchantOrderStatus,
    Notification,
    NotifikasiTipe,
    OrderItem,
)
from app.merchant_order.merchant_order_schema import (
    MerchantOrderStatusUpdate,
    NotificationMarkRead,
)

# Transisi status yang diizinkan
_ALLOWED_TRANSITIONS = {
    MerchantOrderStatus.BARU:       {MerchantOrderStatus.TERBUKA,  MerchantOrderStatus.DIBATALKAN},
    MerchantOrderStatus.TERBUKA:    {MerchantOrderStatus.DIPROSES, MerchantOrderStatus.DIBATALKAN},
    MerchantOrderStatus.DIPROSES:   {MerchantOrderStatus.SELESAI,  MerchantOrderStatus.DIBATALKAN},
    MerchantOrderStatus.SELESAI:    set(),
    MerchantOrderStatus.DIBATALKAN: set(),
}


# ── Eager load ────────────────────────────────────────────────────────────────

def _load_merchant_order(db: Session, order_id: int) -> MerchantOrder:
    """Ambil MerchantOrder beserta semua relasi yang dibutuhkan response."""
    order = (
        db.query(MerchantOrder)
        .options(
            joinedload(MerchantOrder.merchant),
            joinedload(MerchantOrder.customer_order)
                .joinedload(CustomerOrder.customer),
            joinedload(MerchantOrder.customer_order)
                .joinedload(CustomerOrder.dining_table),
            joinedload(MerchantOrder.items)
                .joinedload(OrderItem.product),
        )
        .filter(MerchantOrder.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"Merchant order {order_id} tidak ditemukan")
    return order


# ── Query ─────────────────────────────────────────────────────────────────────

def get_merchant_order_or_404(db: Session, order_id: int) -> MerchantOrder:
    return _load_merchant_order(db, order_id)


def list_merchant_orders(
    db: Session,
    merchant_id: Optional[int] = None,
    status: Optional[MerchantOrderStatus] = None,
    offset: int = 0,
    limit: int = 50,
) -> List[MerchantOrder]:
    query = (
        db.query(MerchantOrder)
        .options(
            joinedload(MerchantOrder.merchant),
            joinedload(MerchantOrder.customer_order)
                .joinedload(CustomerOrder.customer),
            joinedload(MerchantOrder.customer_order)
                .joinedload(CustomerOrder.dining_table),
            joinedload(MerchantOrder.items)
                .joinedload(OrderItem.product),
        )
        .order_by(MerchantOrder.created_at.desc())
    )
    if merchant_id is not None:
        query = query.filter(MerchantOrder.merchant_id == merchant_id)
    if status:
        query = query.filter(MerchantOrder.status == status)
    return query.offset(offset).limit(limit).all()


# ── Update status ─────────────────────────────────────────────────────────────

def update_status(db: Session, order_id: int, data: MerchantOrderStatusUpdate) -> MerchantOrder:
    """Ubah status MerchantOrder lalu sinkronkan status CustomerOrder induk.

    Transisi yang diizinkan:
      baru       → terbuka | dibatalkan
      terbuka    → diproses | dibatalkan
      diproses   → selesai | dibatalkan
      selesai    → (final)
      dibatalkan → (final)

    Jika dibatalkan: stok dikembalikan otomatis.
    Setiap perubahan: notifikasi baru di inbox merchant.
    CustomerOrder diperbarui otomatis via sync_customer_order_status().
    """
    order = _load_merchant_order(db, order_id)
    new_status = data.status

    if new_status == order.status:
        return order

    if new_status not in _ALLOWED_TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Transisi {order.status.value} → {new_status.value} tidak diizinkan",
        )

    # Pembatalan ditangani helper bersama: set status + kembalikan stok +
    # hitung ulang total struk + catat refund parsial bila sudah dibayar.
    if new_status == MerchantOrderStatus.DIBATALKAN:
        cancel_merchant_order(db, order)
    else:
        order.status = new_status

    # Buat notifikasi
    if new_status == MerchantOrderStatus.DIBATALKAN:
        tipe, judul = NotifikasiTipe.ORDER_DIBATALKAN, "Pesanan dibatalkan"
    elif new_status == MerchantOrderStatus.SELESAI:
        tipe, judul = NotifikasiTipe.ORDER_SELESAI, "Pesanan selesai"
    else:
        tipe, judul = NotifikasiTipe.STATUS_BERUBAH, "Status pesanan berubah"

    db.add(Notification(
        merchant_id=order.merchant_id,
        merchant_order_id=order.id,
        tipe=tipe,
        judul=judul,
        pesan=f"{order.order_code} → {new_status.value}",
    ))

    # Sinkronkan status CustomerOrder induk
    if order.customer_order:
        sync_customer_order_status(order.customer_order)

    db.commit()

    # Reload dengan joinedload agar semua relasi terisi di response
    return _load_merchant_order(db, order_id)


# ── Notifikasi ────────────────────────────────────────────────────────────────

def list_notifications(
    db: Session,
    merchant_id: int,
    only_unread: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> List[Notification]:
    query = (
        db.query(Notification)
        .filter(Notification.merchant_id == merchant_id)
        .order_by(Notification.created_at.desc())
    )
    if only_unread:
        query = query.filter(Notification.is_read.is_(False))
    return query.offset(offset).limit(limit).all()


def mark_notifications_read(db: Session, merchant_id: int, data: NotificationMarkRead) -> dict:
    updated = (
        db.query(Notification)
        .filter(Notification.merchant_id == merchant_id, Notification.id.in_(data.ids))
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}


def mark_all_notifications_read(db: Session, merchant_id: int) -> dict:
    updated = (
        db.query(Notification)
        .filter(Notification.merchant_id == merchant_id, Notification.is_read.is_(False))
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}