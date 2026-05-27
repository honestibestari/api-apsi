from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

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


# ── Sinkronisasi status (§D di diagram) ────────────────────────────────────────

def derive_customer_status(merchant_orders) -> CustomerOrderStatus:
    """Turunkan status customer order dari status tiap merchant order.

    Item/merchant order yang dibatalkan tidak diperhitungkan dalam sinkronisasi.
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
    """Perbarui status customer order berdasarkan merchant order-nya.

    Tidak mengubah status pra-bayar (VERIFYING) maupun terminal (DONE);
    caller bertanggung jawab melakukan commit.
    """
    if customer_order.status in (CustomerOrderStatus.VERIFYING, CustomerOrderStatus.DONE):
        return
    customer_order.status = derive_customer_status(customer_order.merchant_orders)


# ── Query ───────────────────────────────────────────────────────────────────────

def get_customer_order_or_404(db: Session, order_id: int) -> CustomerOrder:
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Customer order {order_id} tidak ditemukan")
    return order


def list_customer_orders(
    db: Session,
    status: Optional[CustomerOrderStatus] = None,
    offset: int = 0,
    limit: int = 50,
) -> List[CustomerOrder]:
    query = db.query(CustomerOrder).order_by(CustomerOrder.created_at.desc())
    if status:
        query = query.filter(CustomerOrder.status == status)
    return query.offset(offset).limit(limit).all()


# ── Create ────────────────────────────────────────────────────────────────────

def create_customer_order(db: Session, data: CustomerOrderCreate) -> CustomerOrder:
    """Buat customer order lalu pecah menjadi merchant order per tenant.

    - Pelanggan dibuat baru, atau dipakai ulang bila email cocok.
    - Item dikelompokkan per merchant (berdasar product.merchant_id).
    - Stok berkurang & notifikasi ORDER_BARU dikirim ke tiap merchant.
    """
    table = None
    if data.dining_table_code:
        table = db.query(DiningTable).filter(DiningTable.code == data.dining_table_code).first()
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")

    customer = None
    if data.customer.email:
        customer = db.query(Customer).filter(Customer.email == data.customer.email).first()
    if not customer:
        customer = Customer(
            nama=data.customer.nama,
            email=data.customer.email,
            phone=data.customer.phone,
        )
        db.add(customer)
        db.flush()

    customer_order = CustomerOrder(
        customer_id=customer.id,
        dining_table_id=table.id if table else None,
        tipe_order=data.tipe_order,
        metode_pembayaran=data.metode_pembayaran,
        catatan=data.catatan,
        status=CustomerOrderStatus.VERIFYING,
    )
    db.add(customer_order)
    db.flush()  # dapatkan id + order_code

    # Kelompokkan item per merchant.
    groups: dict[int, list] = {}
    for item in data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} tidak ditemukan")
        if product.stok < item.jumlah:
            raise HTTPException(status_code=400, detail=f"Stok '{product.nama}' tidak cukup")
        groups.setdefault(product.merchant_id, []).append((product, item))

    total_order = 0.0
    for merchant_id, entries in groups.items():
        merchant_order = MerchantOrder(
            order_code=f"{customer_order.order_code}-T{merchant_id}",
            customer_order_id=customer_order.id,
            merchant_id=merchant_id,
            status=MerchantOrderStatus.BARU,
        )
        db.add(merchant_order)
        db.flush()

        subtotal = 0.0
        for product, item in entries:
            line = product.harga * item.jumlah
            subtotal += line
            product.stok -= item.jumlah
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

    customer_order.total_harga = total_order
    db.commit()
    db.refresh(customer_order)
    return customer_order


# ── Transisi status customer ────────────────────────────────────────────────────

def verify_payment(db: Session, order_id: int) -> CustomerOrder:
    """Pembayaran terverifikasi: VERIFYING → OPEN."""
    order = get_customer_order_or_404(db, order_id)
    if order.status != CustomerOrderStatus.VERIFYING:
        raise HTTPException(status_code=400, detail="Order tidak sedang menunggu verifikasi pembayaran")
    order.status = CustomerOrderStatus.OPEN
    db.commit()
    db.refresh(order)
    return order


def confirm_order(db: Session, order_id: int) -> CustomerOrder:
    """Pelanggan konfirmasi pesanan selesai: WAITING_CONFIRMATION → DONE."""
    order = get_customer_order_or_404(db, order_id)
    if order.status != CustomerOrderStatus.WAITING_CONFIRMATION:
        raise HTTPException(status_code=400, detail="Order belum siap dikonfirmasi")
    order.status = CustomerOrderStatus.DONE
    db.commit()
    db.refresh(order)
    return order
