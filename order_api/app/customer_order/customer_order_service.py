from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.customer.customer_model import Customer
from app.customer_order.customer_order_model import CustomerOrder, CustomerOrderStatus
from app.customer_order.customer_order_schema import CustomerOrderCreate
from app.dining_table.dining_table_model import DiningTable
from app.merchant_order.merchant_order_model import (
    MerchantOrder,
    MerchantOrderStatus,
    Notification,
    NotifikasiTipe,
    OrderItem,
)
from app.product.product_model import Product


# ── Eager load ────────────────────────────────────────────────────────────────

def _load_customer_order(db: Session, order_id: int) -> CustomerOrder:
    """Ambil CustomerOrder beserta semua relasi (joinedload bertingkat)."""
    order = (
        db.query(CustomerOrder)
        .options(
            joinedload(CustomerOrder.customer),
            joinedload(CustomerOrder.dining_table),
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


# ── Sinkronisasi status ───────────────────────────────────────────────────────

def derive_customer_status(merchant_orders) -> CustomerOrderStatus:
    """Turunkan status CustomerOrder dari status tiap MerchantOrder.

    Aturan:
    - Semua dibatalkan         → CANCELLED
    - Semua aktif selesai      → WAITING_CONFIRMATION
    - Ada yang sedang diproses → PROCESS
    - Sisanya                  → OPEN
    """
    active = [m for m in merchant_orders if m.status != MerchantOrderStatus.DIBATALKAN]
    if not active:
        return CustomerOrderStatus.CANCELLED
    if all(m.status == MerchantOrderStatus.SELESAI for m in active):
        return CustomerOrderStatus.WAITING_CONFIRMATION
    if any(m.status == MerchantOrderStatus.DIPROSES for m in active):
        return CustomerOrderStatus.PROCESS
    return CustomerOrderStatus.OPEN


def sync_customer_order_status(customer_order: CustomerOrder) -> None:
    """Perbarui status CustomerOrder dari kondisi MerchantOrder-nya.

    Tidak mengubah status VERIFYING (belum bayar) dan DONE (sudah selesai).
    Caller yang bertanggung jawab melakukan commit.
    """
    if customer_order.status in (CustomerOrderStatus.VERIFYING, CustomerOrderStatus.DONE):
        return
    customer_order.status = derive_customer_status(customer_order.merchant_orders)


# ── Query ─────────────────────────────────────────────────────────────────────

def get_customer_order_or_404(db: Session, order_id: int) -> CustomerOrder:
    return _load_customer_order(db, order_id)


def list_customer_orders(
    db: Session,
    status: Optional[CustomerOrderStatus] = None,
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
    return query.offset(offset).limit(limit).all()


# ── Create ────────────────────────────────────────────────────────────────────

def create_customer_order(db: Session, data: CustomerOrderCreate) -> CustomerOrder:
    """Buat CustomerOrder lalu pecah menjadi MerchantOrder per tenant.

    Alur:
    1. Validasi meja (jika dine_in)
    2. Upsert customer (pakai ulang jika email cocok)
    3. Buat CustomerOrder (status: verifying)
    4. Ambil semua product sekaligus (1 query), kelompokkan per merchant_id
    5. Per merchant: buat MerchantOrder + OrderItem + kurangi stok + notifikasi
    6. Hitung total_harga, commit, reload dengan joinedload
    """

    # 1. Validasi meja
    table = None
    if data.dining_table_code:
        table = (
            db.query(DiningTable)
            .filter(DiningTable.code == data.dining_table_code)
            .first()
        )
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")

    # 2. Upsert customer
    def _upsert_customer(db, data_customer):
 
        customer = None
    
        # Cari by email
        if data_customer.email:
            customer = (
                db.query(Customer)
                .filter(Customer.email == data_customer.email)
                .first()
            )
    
        # Kalau tidak ketemu by email, cari by phone
        if not customer and data_customer.phone:
            customer = (
                db.query(Customer)
                .filter(Customer.phone == data_customer.phone)
                .first()
            )
    
        if customer:
            # Customer lama ditemukan — update data jika ada perubahan
            if data_customer.nama and customer.nama != data_customer.nama:
                customer.nama = data_customer.nama
            if data_customer.phone and customer.phone != data_customer.phone:
                customer.phone = data_customer.phone
            if data_customer.email and customer.email != data_customer.email:
                customer.email = data_customer.email
            db.flush()
        else:
            # Customer baru
            customer = Customer(
                nama  = data_customer.nama,
                email = data_customer.email,
                phone = data_customer.phone,
            )
            db.add(customer)
            db.flush()
    
        return customer

    # 3. Buat CustomerOrder
    customer_order = CustomerOrder(
        customer_id=customer.id,
        dining_table_id=table.id if table else None,
        tipe_order=data.tipe_order,
        metode_pembayaran=data.metode_pembayaran,
        catatan=data.catatan,
        status=CustomerOrderStatus.VERIFYING,
    )
    db.add(customer_order)
    db.flush()  # agar order_code ter-generate

    # 4. Ambil semua product sekaligus, kelompokkan per merchant
    product_ids = [i.product_id for i in data.items]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    groups: dict[int, list] = {}
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
            order_code=f"{customer_order.order_code}-T{merchant_id}",
            customer_order_id=customer_order.id,
            merchant_id=merchant_id,
            status=MerchantOrderStatus.BARU,
        )
        db.add(merchant_order)
        db.flush()  # agar merchant_order.id tersedia untuk OrderItem

        subtotal = 0.0
        for product, item in entries:
            line = product.harga * item.jumlah
            subtotal += line
            product.stok -= item.jumlah  # kurangi stok

            db.add(OrderItem(
                merchant_order_id=merchant_order.id,
                product_id=product.id,
                jumlah=item.jumlah,
                harga_satuan=product.harga,
                subtotal=line,
                varian=item.varian,
            ))

        merchant_order.subtotal = subtotal
        merchant_order.total_harga = subtotal + merchant_order.biaya_penanganan
        total_order += merchant_order.total_harga

        db.add(Notification(
            merchant_id=merchant_id,
            merchant_order_id=merchant_order.id,
            tipe=NotifikasiTipe.ORDER_BARU,
            judul="Pesanan baru masuk",
            pesan=f"Pesanan {merchant_order.order_code} menunggu konfirmasi.",
        ))

    # 6. Simpan total dan commit
    customer_order.total_harga = total_order
    db.commit()

    # Reload dengan joinedload agar semua relasi terisi di response
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