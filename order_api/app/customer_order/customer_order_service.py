from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.customer.customer_model import Customer
from app.customer_order.customer_order_model import CustomerOrder, CustomerOrderStatus
from app.customer_order.customer_order_schema import CustomerOrderCreate
from app.dining_table.dining_table_model import DiningTable
from app.payment_method.payment_method_model import PaymentMethod
from app.merchant_order.merchant_order_model import (
    MerchantOrder,
    MerchantOrderStatus,
    Notification,
    NotifikasiTipe,
    OrderItem,
)
from app.payment.payment_model import Payment, StatusPembayaran
from app.product.product_model import Product


# ── Eager load ────────────────────────────────────────────────────────────────

def _load_customer_order(db: Session, order_id: int) -> CustomerOrder:
    """Ambil CustomerOrder beserta semua relasi (joinedload bertingkat)."""
    order = (
        db.query(CustomerOrder)
        .options(
            joinedload(CustomerOrder.customer),
            joinedload(CustomerOrder.dining_table),
            joinedload(CustomerOrder.metode),
            joinedload(CustomerOrder.merchant_orders)
                .joinedload(MerchantOrder.merchant),
            joinedload(CustomerOrder.merchant_orders)
                .joinedload(MerchantOrder.items)
                .joinedload(OrderItem.product),
        )
        .filter(CustomerOrder.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"Customer order {order_id} tidak ditemukan")
    return order


# ── Upsert customer — di LUAR create_customer_order ──────────────────────────

def _upsert_customer(db: Session, data_customer) -> Customer:
    """Ambil customer lama (by EMAIL) atau buat baru.

    Email = satu-satunya kunci identitas (unik). Phone hanya data pelengkap:
    selalu diperbarui ke nilai terbaru, boleh berubah/duplikat tanpa konflik.
    """
    nama_default = data_customer.nama or data_customer.email.split("@")[0]

    customer = (
        db.query(Customer)
        .filter(Customer.email == data_customer.email)
        .first()
    )

    if customer:
        # Customer lama — perbarui data terbaru.
        if data_customer.nama and customer.nama != data_customer.nama:
            customer.nama = data_customer.nama
        # Phone bukan kunci → boleh berubah kapan saja (termasuk dikosongkan? tidak,
        # hanya timpa bila dikirim agar tidak menghapus data lama tanpa sengaja).
        if data_customer.phone and customer.phone != data_customer.phone:
            customer.phone = data_customer.phone
        db.flush()
    else:
        customer = Customer(
            nama  = nama_default,
            email = data_customer.email,
            phone = data_customer.phone,
        )
        db.add(customer)
        db.flush()

    return customer


# ── Pembatalan & refund parsial ─────────────────────────────────────────────

def _recompute_order_total(order: CustomerOrder) -> None:
    """Total struk = jumlah total_harga merchant order yang TIDAK dibatalkan."""
    order.total_harga = sum(
        mo.total_harga for mo in order.merchant_orders
        if mo.status != MerchantOrderStatus.DIBATALKAN
    )


def _order_is_paid(db: Session, order: CustomerOrder) -> bool:
    """True bila ada pembayaran LUNAS untuk order ini (perlu refund saat dibatalkan)."""
    return (
        db.query(Payment)
        .filter(
            Payment.id_pesanan == order.id,
            Payment.status_pembayaran == StatusPembayaran.LUNAS,
        )
        .first()
        is not None
    )


def cancel_merchant_order(db: Session, mo: MerchantOrder) -> None:
    """Batalkan SATU merchant order secara konsisten:

    • status → dibatalkan (idempotent),
    • kembalikan stok produk (stok di-reserve saat order dibuat, jadi selalu
      dikembalikan saat dibatalkan),
    • hitung ulang total struk induk.

    Refund TIDAK dibuat di sini. Refund dibentuk saat CUSTOMER ORDER selesai
    keseluruhan (done/cancelled): bila ada ≥1 merchant order dibatalkan & order
    sudah dibayar, sweep membuat satu Refund agregat lalu mengirim link pilih
    metode ke email customer.

    Tidak commit — pemanggil yang commit. Tidak membuat notifikasi & tidak
    men-sync status struk (diserahkan ke pemanggil sesuai konteksnya).
    """
    if mo.status == MerchantOrderStatus.DIBATALKAN:
        return

    mo.status = MerchantOrderStatus.DIBATALKAN

    # Stok dikonsumsi saat order dibuat → selalu kembalikan saat dibatalkan.
    for item in mo.items:
        if item.product:
            item.product.stok += item.jumlah

    order = mo.customer_order
    if order is None:
        return

    _recompute_order_total(order)


# ── Sinkronisasi status ───────────────────────────────────────────────────────

def derive_customer_status(merchant_orders) -> CustomerOrderStatus:
    """Turunkan status CustomerOrder dari status tiap MerchantOrder.

    Merchant order 'dibatalkan' diabaikan; hanya bila SEMUA dibatalkan struk
    dianggap cancelled. Begitu ada tenant yang 'selesai' atau 'diproses'
    (sudah ada aktivitas), struk dianggap 'process' — 'open' hanya saat semua
    tenant masih 'terbuka'/'baru'.
    """
    active = [m for m in merchant_orders if m.status != MerchantOrderStatus.DIBATALKAN]
    if not active:
        return CustomerOrderStatus.CANCELLED
    if all(m.status == MerchantOrderStatus.SELESAI for m in active):
        return CustomerOrderStatus.WAITING_CONFIRMATION
    if any(m.status in (MerchantOrderStatus.DIPROSES, MerchantOrderStatus.SELESAI) for m in active):
        return CustomerOrderStatus.PROCESS
    return CustomerOrderStatus.OPEN


def _auto_cancel_stale_merchant_orders(db: Session, customer_order: CustomerOrder) -> bool:
    """Batalkan merchant order yang masih 'terbuka' melewati batas waktu putusan.

    Merchant yang tidak confirm/tolak dalam merchant_decide_timeout_seconds →
    otomatis 'dibatalkan'. Stok dikembalikan & refund parsial dicatat lewat
    cancel_merchant_order(). Return True bila ada perubahan.
    """
    secs = settings.merchant_decide_timeout_seconds
    if secs <= 0 or customer_order.status in (
        CustomerOrderStatus.VERIFYING, CustomerOrderStatus.DONE, CustomerOrderStatus.CANCELLED
    ):
        return False
    now = datetime.now(timezone.utc)
    changed = False
    for mo in customer_order.merchant_orders:
        if mo.status != MerchantOrderStatus.TERBUKA:
            continue
        ref = mo.updated_at or mo.created_at      # waktu mo menjadi 'terbuka'
        if ref is None:
            continue
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        if (now - ref).total_seconds() >= secs:
            cancel_merchant_order(db, mo)
            db.add(Notification(
                merchant_id       = mo.merchant_id,
                merchant_order_id = mo.id,
                tipe              = NotifikasiTipe.ORDER_DIBATALKAN,
                judul             = "Pesanan dibatalkan otomatis",
                pesan             = f"{mo.order_code} dibatalkan karena tidak direspons tepat waktu.",
            ))
            changed = True
    return changed


def sync_customer_order_status(customer_order: CustomerOrder) -> None:
    """Perbarui status CustomerOrder dari kondisi MerchantOrder-nya."""
    if customer_order.status in (CustomerOrderStatus.VERIFYING, CustomerOrderStatus.DONE):
        return
    customer_order.status = derive_customer_status(customer_order.merchant_orders)


def refresh_order_state(db: Session, customer_order: CustomerOrder) -> None:
    """Terapkan timeout merchant + turunkan ulang status struk. Commit bila berubah."""
    before = customer_order.status
    timed_out = _auto_cancel_stale_merchant_orders(db, customer_order)
    sync_customer_order_status(customer_order)
    if timed_out or customer_order.status != before:
        db.commit()


# ── Query ─────────────────────────────────────────────────────────────────────

def get_customer_order_or_404(db: Session, order_id: int) -> CustomerOrder:
    order = _load_customer_order(db, order_id)
    refresh_order_state(db, order)   # terapkan timeout merchant + status terkini
    return order


def list_customer_orders(
    db: Session,
    status: Optional[CustomerOrderStatus] = None,
    customer_id: Optional[int] = None,
    offset: int = 0,
    limit: int = 50,
) -> List[CustomerOrder]:
    query = (
        db.query(CustomerOrder)
        .options(
            joinedload(CustomerOrder.customer),
            joinedload(CustomerOrder.dining_table),
            joinedload(CustomerOrder.merchant_orders),
        )
        .order_by(CustomerOrder.created_at.desc())
    )
    if status:
        query = query.filter(CustomerOrder.status == status)
    if customer_id is not None:
        query = query.filter(CustomerOrder.customer_id == customer_id)
    return query.offset(offset).limit(limit).all()


# ── Create ────────────────────────────────────────────────────────────────────

def create_customer_order(db: Session, data: CustomerOrderCreate) -> CustomerOrder:
    """Buat CustomerOrder lalu pecah menjadi MerchantOrder per tenant.

    Alur:
    1. Upsert customer (pakai ulang jika email/phone cocok)
    1b. Batasi jumlah pesanan aktif per akun customer
    2. Validasi meja (jika dine_in)
    3. Buat CustomerOrder (status: verifying)
    4. Ambil semua product sekaligus (1 query), kelompokkan per merchant_id
    5. Per merchant: buat MerchantOrder + OrderItem + kurangi stok + notifikasi
    6. Hitung total_harga, commit, reload dengan joinedload
    """

    # 1. Upsert customer
    customer = _upsert_customer(db, data.customer)

    # 1b. Batasi pesanan aktif per akun (belum done/cancelled).
    max_aktif = settings.max_active_orders_per_customer
    if max_aktif > 0:
        aktif = (
            db.query(CustomerOrder)
            .filter(
                CustomerOrder.customer_id == customer.id,
                CustomerOrder.status.notin_([
                    CustomerOrderStatus.DONE,
                    CustomerOrderStatus.CANCELLED,
                ]),
            )
            .count()
        )
        if aktif >= max_aktif:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Maksimal {max_aktif} pesanan aktif per akun. "
                    "Selesaikan pesanan sebelumnya dulu."
                ),
            )

    # 2. Validasi meja — harus ada DAN aktif (selaras dengan endpoint /scan).
    #    Meja yang dinonaktifkan admin tidak boleh dipakai walau code-nya masih
    #    tersimpan di sesi customer.
    table = None
    if data.dining_table_code:
        table = (
            db.query(DiningTable)
            .filter(DiningTable.code == data.dining_table_code)
            .first()
        )
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")
        if not table.is_active:
            raise HTTPException(status_code=400, detail="Meja sedang tidak aktif")

    # 2b. Validasi metode pembayaran: harus ada & aktif.
    metode = (
        db.query(PaymentMethod)
        .filter(PaymentMethod.id == data.metode_pembayaran_id)
        .first()
    )
    if not metode:
        raise HTTPException(status_code=404, detail="Metode pembayaran tidak ditemukan")
    if not metode.is_active:
        raise HTTPException(status_code=400, detail=f"Metode '{metode.nama_metode}' sedang tidak aktif")

    # 3. Buat CustomerOrder
    customer_order = CustomerOrder(
        customer_id          = customer.id,
        dining_table_id      = table.id if table else None,
        tipe_order           = data.tipe_order,
        metode_pembayaran_id = metode.id,
        catatan              = data.catatan,
        status               = CustomerOrderStatus.VERIFYING,
    )
    db.add(customer_order)
    db.flush()  # agar order_code ter-generate

    # 4. Ambil semua product sekaligus, kelompokkan per merchant
    product_ids = [i.product_id for i in data.items]
    products    = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    groups: dict = {}
    for item in data.items:
        product = product_map.get(item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} tidak ditemukan")
        if product.stok < item.jumlah:
            raise HTTPException(status_code=400, detail=f"Stok '{product.nama}' tidak cukup")
        groups.setdefault(product.merchant_id, []).append((product, item))

    # 5. Buat MerchantOrder per tenant
    total_order = 0.0
    for merchant_id, entries in groups.items():
        merchant_order = MerchantOrder(
            order_code        = f"{customer_order.order_code}-T{merchant_id}",
            customer_order_id = customer_order.id,
            merchant_id       = merchant_id,
            status            = MerchantOrderStatus.BARU,
            metode_pembayaran = metode.nama_metode
        )
        db.add(merchant_order)
        db.flush()

        subtotal = 0.0
        for product, item in entries:
            line      = product.harga * item.jumlah
            subtotal += line
            # Stok dikonsumsi saat order DIBUAT (di-reserve), dikembalikan saat
            # dibatalkan. Mencegah oversell dari banyak order yang menunggu bayar.
            product.stok -= item.jumlah

            db.add(OrderItem(
                merchant_order_id = merchant_order.id,
                product_id        = product.id,
                jumlah            = item.jumlah,
                harga_satuan      = product.harga,
                subtotal          = line,
                varian            = item.varian,
            ))

        merchant_order.subtotal    = subtotal
        merchant_order.total_harga = subtotal + merchant_order.biaya_penanganan
        total_order               += merchant_order.total_harga

        db.add(Notification(
            merchant_id       = merchant_id,
            merchant_order_id = merchant_order.id,
            tipe              = NotifikasiTipe.ORDER_BARU,
            judul             = "Pesanan baru masuk",
            pesan             = f"Pesanan {merchant_order.order_code} menunggu konfirmasi.",
        ))

    # 6. Simpan total dan commit
    customer_order.total_harga = total_order
    db.commit()

    return _load_customer_order(db, customer_order.id)


# ── Transisi status CustomerOrder ─────────────────────────────────────────────

def verify_payment(db: Session, order_id: int) -> CustomerOrder:
    """Pembayaran terverifikasi: VERIFYING → OPEN."""
    order = _load_customer_order(db, order_id)
    if order.status != CustomerOrderStatus.VERIFYING:
        raise HTTPException(status_code=400, detail="Order tidak sedang menunggu verifikasi pembayaran")
    order.status = CustomerOrderStatus.OPEN
    db.commit()
    return _load_customer_order(db, order_id)


def confirm_order(db: Session, order_id: int) -> CustomerOrder:
    """Pelanggan konfirmasi pesanan selesai: WAITING_CONFIRMATION → DONE."""
    order = _load_customer_order(db, order_id)
    if order.status != CustomerOrderStatus.WAITING_CONFIRMATION:
        raise HTTPException(status_code=400, detail="Order belum siap dikonfirmasi")
    order.status = CustomerOrderStatus.DONE
    db.commit()
    return _load_customer_order(db, order_id)


def customer_cancel_merchant_order(
    db: Session, order_id: int, merchant_order_id: int
) -> CustomerOrder:
    """Pelanggan membatalkan SATU tenant yang telat diproses (refund parsial).

    Hanya berlaku untuk merchant order milik struk ini yang berstatus 'diproses'
    DAN sudah melewati batas waktu penyiapan (is_prep_overdue). Tenant lain pada
    struk yang sama TIDAK terpengaruh. Stok dikembalikan, refund parsial dicatat,
    total struk dihitung ulang, status struk di-sync.
    """
    order = _load_customer_order(db, order_id)
    mo = next((m for m in order.merchant_orders if m.id == merchant_order_id), None)
    if mo is None:
        raise HTTPException(404, "Pesanan tenant tidak ditemukan pada struk ini")
    if mo.status != MerchantOrderStatus.DIPROSES:
        raise HTTPException(400, "Hanya pesanan tenant yang sedang diproses yang bisa dibatalkan")
    if not mo.is_prep_overdue:
        raise HTTPException(400, "Pesanan tenant belum melewati batas waktu — belum bisa dibatalkan")

    cancel_merchant_order(db, mo)  # dibatalkan + stok kembali + refund parsial
    db.add(Notification(
        merchant_id       = mo.merchant_id,
        merchant_order_id = mo.id,
        tipe              = NotifikasiTipe.ORDER_DIBATALKAN,
        judul             = "Pesanan dibatalkan pelanggan",
        pesan             = f"{mo.order_code} dibatalkan pelanggan karena melewati batas waktu penyiapan.",
    ))
    sync_customer_order_status(order)
    db.commit()
    return _load_customer_order(db, order_id)