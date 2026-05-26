from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.order import order_service
from app.order.order_model import OrderStatus, TipeOrder
from app.order.order_schema import (
    NotificationMarkRead,
    NotificationOut,
    OrderCreate,
    OrderOut,
    OrderStats,
    OrderStatusUpdate,
    OrderSummary,
)
from app.order.order_service import _preview_items

router = APIRouter(tags=["Orders"])


# ── Customer ──────────────────────────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Customer] Buat order baru",
)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """
    Buat order baru. Sebelum ini, customer GET /products?merchant_id=X untuk dapat product_id.

    Status awal otomatis: baru
    Stok otomatis berkurang.
    Notifikasi otomatis masuk ke inbox merchant.
    dining_table_code wajib jika tipe_order = dine_in.
    """
    return order_service.create_order(db, data)


@router.get(
    "/orders/{order_id}",
    response_model=OrderOut,
    summary="[Customer & Merchant] Detail order",
)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """
    Detail lengkap satu order. Response sudah include nama & harga product di setiap item.
    """
    return order_service.get_order_or_404(db, order_id)


# ── Merchant ──────────────────────────────────────────────────────────────────

@router.get(
    "/orders/stats/{merchant_id}",
    response_model=OrderStats,
    summary="[Merchant] Statistik harian dashboard",
)
def get_order_stats(merchant_id: int, db: Session = Depends(get_db)):
    """
    Kartu ringkasan harian:
    - pesanan_baru: jumlah order status baru hari ini
    - pesanan_diproses: jumlah order status diproses hari ini
    - pendapatan_hari_ini: total dari order selesai hari ini
    - notifikasi_belum_dibaca: jumlah inbox yang belum dibaca
    """
    return order_service.get_order_stats(db, merchant_id)


@router.get(
    "/orders",
    response_model=List[OrderSummary],
    summary="[Merchant] List pesanan masuk",
)
def list_orders(
    merchant_id:     Optional[int]         = Query(None, description="Filter per merchant"),
    dining_table_id: Optional[int]         = Query(None, description="Filter per meja"),
    status:          Optional[OrderStatus]  = Query(None, description="baru | diproses | selesai | dibatalkan"),
    tipe_order:      Optional[TipeOrder]   = Query(None, description="dine_in | takeaway"),
    offset:          int                   = Query(0, ge=0),
    limit:           int                   = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    List order dengan filter. Contoh:
    - Order baru: ?merchant_id=1&status=baru
    - Per meja: ?dining_table_id=3
    - Dine in diproses: ?merchant_id=1&status=diproses&tipe_order=dine_in
    """
    orders = order_service.list_orders(
        db,
        merchant_id=merchant_id,
        dining_table_id=dining_table_id,
        status=status,
        tipe_order=tipe_order,
        offset=offset,
        limit=limit,
    )
    result = []
    for o in orders:
        summary = OrderSummary.model_validate(o)
        summary.preview_items = _preview_items(o.items)
        result.append(summary)
    return result


@router.put(
    "/orders/{order_id}/status",
    response_model=OrderOut,
    summary="[Merchant] Update status order",
)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Ubah status order. Transisi yang diizinkan:

      baru       → diproses   (Terima Pesanan)
      baru       → dibatalkan (Tolak)
      diproses   → selesai    (Pesanan Siap)
      diproses   → dibatalkan (Batalkan)
      selesai    → (final)
      dibatalkan → (final)

    Jika dibatalkan: stok dikembalikan otomatis.
    Setiap perubahan: notifikasi baru di inbox merchant.
    """
    return order_service.update_order_status(db, order_id, data)


@router.delete(
    "/orders/{order_id}",
    summary="[Merchant] Hapus order yang masih baru",
)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """
    Hapus order hanya jika status masih baru.
    Jika sudah diproses, gunakan PUT status → dibatalkan.
    Stok dikembalikan otomatis.
    """
    return order_service.delete_order(db, order_id)


# ── Notifikasi ────────────────────────────────────────────────────────────────

@router.get(
    "/notifications/{merchant_id}",
    response_model=List[NotificationOut],
    summary="[Merchant] List inbox notifikasi",
)
def list_notifications(
    merchant_id: int,
    only_unread: bool = Query(False, description="true = belum dibaca saja"),
    offset:      int  = Query(0, ge=0),
    limit:       int  = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return order_service.list_notifications(
        db, merchant_id, only_unread=only_unread, offset=offset, limit=limit
    )


@router.post(
    "/notifications/{merchant_id}/read",
    summary="[Merchant] Tandai notifikasi tertentu sudah dibaca",
)
def mark_read(merchant_id: int, data: NotificationMarkRead, db: Session = Depends(get_db)):
    """Body: { "ids": [1, 2, 3] }"""
    return order_service.mark_notifications_read(db, merchant_id, data)


@router.post(
    "/notifications/{merchant_id}/read-all",
    summary="[Merchant] Tandai semua notifikasi sudah dibaca",
)
def mark_all_read(merchant_id: int, db: Session = Depends(get_db)):
    return order_service.mark_all_notifications_read(db, merchant_id)