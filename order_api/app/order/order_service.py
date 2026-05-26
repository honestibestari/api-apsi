from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.dining_table.dining_table_model import DiningTable
from app.merchant.merchant_model import Merchant
from app.order.order_model import (
    Notification,
    NotifikasiTipe,
    Order,
    OrderItem,
    OrderStatus,
    TipeOrder,
)
from app.order.order_schema import (
    NotificationMarkRead,
    OrderCreate,
    OrderStats,
    OrderStatusUpdate,
)
from app.product.product_model import Product


# ── Helpers ───────────────────────────────────────────────────────────────────

def _buat_notifikasi(
    db: Session,
    merchant_id: int,
    order: Order,
    tipe: NotifikasiTipe,
    judul: str,
    pesan: str,
) -> None:
    db.add(Notification(
        merchant_id=merchant_id,
        order_id=order.id,
        tipe=tipe,
        judul=judul,
        pesan=pesan,
    ))


def _preview_items(items: List[OrderItem]) -> str:
    parts = []
    for it in items[:3]:
        nama = it.product.nama if it.product else f"Product#{it.product_id}"
        parts.append(f"{it.jumlah}x {nama}")
    result = ", ".join(parts)
    if len(items) > 3:
        result += f", +{len(items) - 3} lainnya"
    return result


def _load_order(db: Session, order_id: int) -> Order:
    """Ambil order dengan eager load semua relasi yang dibutuhkan."""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.dining_table),
            joinedload(Order.merchant),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(404, f"Order ID {order_id} tidak ditemukan")
    return order


# ── CRUD Order ────────────────────────────────────────────────────────────────

def get_order_or_404(db: Session, order_id: int) -> Order:
    return _load_order(db, order_id)


def create_order(db: Session, data: OrderCreate) -> Order:
    # 1. Validasi merchant
    merchant = db.query(Merchant).filter(Merchant.id == data.merchant_id).first()
    if not merchant:
        raise HTTPException(404, f"Merchant ID {data.merchant_id} tidak ditemukan")

    # 2. Validasi meja (wajib untuk dine_in)
    table_id: Optional[int] = None
    if data.tipe_order == TipeOrder.DINE_IN and data.dining_table_code:
        table = (
            db.query(DiningTable)
            .filter(
                DiningTable.code == data.dining_table_code,
                DiningTable.is_active.is_(True),
            )
            .first()
        )
        if not table:
            raise HTTPException(404, f"Meja '{data.dining_table_code}' tidak ditemukan atau tidak aktif")
        table_id = table.id

    # 3. Validasi product & stok (1 query untuk semua product)
    product_ids = [i.product_id for i in data.items]
    products    = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    order_items: List[OrderItem] = []
    subtotal_total = 0.0

    for item_data in data.items:
        product = product_map.get(item_data.product_id)

        if not product:
            raise HTTPException(404, f"Product ID {item_data.product_id} tidak ditemukan")
        if product.merchant_id != data.merchant_id:
            raise HTTPException(400, f"Product '{product.nama}' bukan milik merchant ini")
        if product.stok < item_data.jumlah:
            raise HTTPException(
                400,
                f"Stok '{product.nama}' tidak cukup "
                f"(tersedia: {product.stok}, diminta: {item_data.jumlah})",
            )

        product.stok -= item_data.jumlah
        sub = product.harga * item_data.jumlah
        subtotal_total += sub

        order_items.append(OrderItem(
            product_id   = product.id,
            jumlah       = item_data.jumlah,
            harga_satuan = product.harga,
            subtotal     = sub,
            varian       = item_data.varian,
        ))

    # 4. Hitung harga
    BIAYA_PENANGANAN = 1000.0
    total = subtotal_total + BIAYA_PENANGANAN

    # 5. Simpan order
    order = Order(
        merchant_id       = data.merchant_id,
        dining_table_id   = table_id,
        nama_pelanggan    = data.nama_pelanggan,
        tipe_order        = data.tipe_order,
        catatan           = data.catatan,
        metode_pembayaran = data.metode_pembayaran,
        subtotal          = subtotal_total,
        biaya_penanganan  = BIAYA_PENANGANAN,
        total_harga       = total,
        items             = order_items,
    )
    db.add(order)
    db.flush()

    # 6. Notifikasi ke merchant
    _buat_notifikasi(
        db, data.merchant_id, order,
        tipe  = NotifikasiTipe.ORDER_BARU,
        judul = "Order Baru Masuk!",
        pesan = f"{data.nama_pelanggan}, #{order.order_code}, {_preview_items(order_items)}",
    )

    db.commit()
    return _load_order(db, order.id)


def list_orders(
    db: Session,
    merchant_id:     Optional[int]         = None,
    dining_table_id: Optional[int]         = None,
    status:          Optional[OrderStatus]  = None,
    tipe_order:      Optional[TipeOrder]   = None,
    offset:          int                   = 0,
    limit:           int                   = 50,
) -> List[Order]:
    limit = min(limit, 200)
    query = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .order_by(Order.created_at.desc())
    )
    if merchant_id:
        query = query.filter(Order.merchant_id == merchant_id)
    if dining_table_id:
        query = query.filter(Order.dining_table_id == dining_table_id)
    if status:
        query = query.filter(Order.status == status)
    if tipe_order:
        query = query.filter(Order.tipe_order == tipe_order)

    return query.offset(offset).limit(limit).all()


def update_order_status(db: Session, order_id: int, data: OrderStatusUpdate) -> Order:
    """
    Transisi status yang diizinkan:
      baru       → diproses | dibatalkan
      diproses   → selesai  | dibatalkan
      selesai    → (final)
      dibatalkan → (final)

    Jika dibatalkan: stok dikembalikan & notifikasi dibuat.
    """
    order = _load_order(db, order_id)

    ALLOWED = {
        OrderStatus.BARU:       {OrderStatus.DIPROSES,  OrderStatus.DIBATALKAN},
        OrderStatus.DIPROSES:   {OrderStatus.SELESAI,   OrderStatus.DIBATALKAN},
        OrderStatus.SELESAI:    set(),
        OrderStatus.DIBATALKAN: set(),
    }

    allowed = ALLOWED.get(order.status, set())
    if data.status not in allowed:
        raise HTTPException(
            400,
            f"Tidak bisa ubah status '{order.status}' → '{data.status}'. "
            f"Yang diizinkan: {[s.value for s in allowed] or 'tidak ada (status final)'}",
        )

    if data.status == OrderStatus.DIBATALKAN:
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stok += item.jumlah

    order.status = data.status

    NOTIF_MAP = {
        OrderStatus.DIPROSES:   (NotifikasiTipe.STATUS_BERUBAH,   "Pesanan Diproses",   f"#{order.order_code} sedang diproses"),
        OrderStatus.SELESAI:    (NotifikasiTipe.ORDER_SELESAI,    "Order Selesai",      f"#{order.order_code} selesai — {order.nama_pelanggan}"),
        OrderStatus.DIBATALKAN: (NotifikasiTipe.ORDER_DIBATALKAN, "Pesanan Dibatalkan", f"#{order.order_code} dibatalkan"),
    }
    if data.status in NOTIF_MAP:
        tipe, judul, pesan = NOTIF_MAP[data.status]
        _buat_notifikasi(db, order.merchant_id, order, tipe, judul, pesan)

    db.commit()
    return _load_order(db, order.id)


def delete_order(db: Session, order_id: int) -> dict:
    """Hapus order — hanya boleh jika status masih BARU. Stok dikembalikan."""
    order = _load_order(db, order_id)

    if order.status != OrderStatus.BARU:
        raise HTTPException(
            400,
            f"Order hanya bisa dihapus jika masih 'baru'. "
            f"Status saat ini: '{order.status}'. Gunakan PUT status → 'dibatalkan'.",
        )

    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stok += item.jumlah

    code = order.order_code
    db.delete(order)
    db.commit()
    return {"message": f"Order #{code} berhasil dihapus", "id": order_id}


# ── Dashboard Stats ───────────────────────────────────────────────────────────

def get_order_stats(db: Session, merchant_id: int) -> OrderStats:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    def count_status(s: OrderStatus) -> int:
        return (
            db.query(func.count(Order.id))
            .filter(Order.merchant_id == merchant_id, Order.status == s, Order.created_at >= today_start)
            .scalar() or 0
        )

    pendapatan = (
        db.query(func.sum(Order.total_harga))
        .filter(Order.merchant_id == merchant_id, Order.status == OrderStatus.SELESAI, Order.created_at >= today_start)
        .scalar() or 0.0
    )

    unread = (
        db.query(func.count(Notification.id))
        .filter(Notification.merchant_id == merchant_id, Notification.is_read.is_(False))
        .scalar() or 0
    )

    return OrderStats(
        pesanan_baru            = count_status(OrderStatus.BARU),
        pesanan_diproses        = count_status(OrderStatus.DIPROSES),
        pendapatan_hari_ini     = pendapatan,
        notifikasi_belum_dibaca = unread,
    )


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
    rows = (
        db.query(Notification)
        .filter(Notification.merchant_id == merchant_id, Notification.id.in_(data.ids))
        .all()
    )
    for n in rows:
        n.is_read = True
    db.commit()
    return {"message": f"{len(rows)} notifikasi ditandai sudah dibaca"}


def mark_all_notifications_read(db: Session, merchant_id: int) -> dict:
    rows = (
        db.query(Notification)
        .filter(Notification.merchant_id == merchant_id, Notification.is_read.is_(False))
        .all()
    )
    for n in rows:
        n.is_read = True
    db.commit()
    return {"message": f"{len(rows)} notifikasi ditandai sudah dibaca"}