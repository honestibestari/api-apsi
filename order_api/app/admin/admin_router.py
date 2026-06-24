from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.auth import require_admin
from app.core.database import get_db
from app.category.category_model import Category
from app.customer_order.customer_order_model import CustomerOrder, CustomerOrderStatus
from app.merchant.merchant_model import Merchant, MerchantStatus
from app.product.product_model import Product
from app.merchant_order.merchant_order_model import (
    MerchantOrder,
    MerchantOrderStatus,
    Notification,
    NotifikasiTipe,
)
from app.customer.customer_model import Customer
from app.withdrawal.withdrawal_model import Withdrawal, WithdrawalStatus
from app.platform_setting import platform_setting_service as fee_svc

router = APIRouter(prefix="/admin", tags=["Admin"])

# Waktu Indonesia Barat (UTC+7, tanpa DST). Semua batas "hari ini/kemarin/minggu
# ini" dihitung relatif terhadap kalender WIB, lalu dikonversi ke UTC-naive untuk
# dibandingkan dengan kolom created_at (disimpan UTC oleh func.now()).
WIB = timezone(timedelta(hours=7))


def _wib_day_bounds_utc(days_ago: int = 0):
    """(start, end) satu hari kalender WIB, sebagai datetime UTC-naive."""
    day = (datetime.now(WIB) - timedelta(days=days_ago)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = day.astimezone(timezone.utc).replace(tzinfo=None)
    end = (day + timedelta(days=1)).astimezone(timezone.utc).replace(tzinfo=None)
    return start, end


def _to_wib_date(dt: datetime):
    """Tanggal kalender WIB dari created_at (aware → konversi, naive → anggap UTC)."""
    if dt.tzinfo is not None:
        return dt.astimezone(WIB).date()
    return (dt + timedelta(hours=7)).date()


# ── Dashboard ringkasan ───────────────────────────────────────────────────────

@router.get("/dashboard", summary="Ringkasan statistik sistem")
def dashboard(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Statistik untuk halaman dashboard admin.

    Definisi "total transaksi" = SUM(CustomerOrder.total_harga) dengan status
    DONE (struk global yang tuntas). Semua metrik harian memakai kalender WIB.
    """
    DONE = CustomerOrderStatus.DONE
    ACTIVE_STATUSES = [
        CustomerOrderStatus.VERIFYING,
        CustomerOrderStatus.OPEN,
        CustomerOrderStatus.PROCESS,
        CustomerOrderStatus.WAITING_CONFIRMATION,
    ]

    today_start, today_end = _wib_day_bounds_utc(0)
    yest_start,  yest_end  = _wib_day_bounds_utc(1)
    week_start,  _         = _wib_day_bounds_utc(6)   # 7 hari termasuk hari ini
    chart_start, _         = _wib_day_bounds_utc(7)   # 8 titik untuk grafik

    def _done_sum(start, end) -> float:
        return float(
            db.query(func.coalesce(func.sum(CustomerOrder.total_harga), 0.0))
            .filter(CustomerOrder.status == DONE)
            .filter(CustomerOrder.created_at >= start, CustomerOrder.created_at < end)
            .scalar() or 0.0
        )

    # ── Kartu KPI ──────────────────────────────────────────────────────────────
    transaksi_today     = _done_sum(today_start, today_end)
    transaksi_yesterday = _done_sum(yest_start, yest_end)

    orders_today = (
        db.query(func.count(CustomerOrder.id))
        .filter(CustomerOrder.created_at >= today_start, CustomerOrder.created_at < today_end)
        .scalar()
    )
    completed_today = (
        db.query(func.count(CustomerOrder.id))
        .filter(CustomerOrder.status == DONE)
        .filter(CustomerOrder.created_at >= today_start, CustomerOrder.created_at < today_end)
        .scalar()
    )
    active_transactions = (
        db.query(func.count(CustomerOrder.id))
        .filter(CustomerOrder.status.in_(ACTIVE_STATUSES))
        .scalar()
    )

    # Order multi-tenant hari ini = CustomerOrder dengan > 1 merchant_order.
    multi_ids = (
        db.query(MerchantOrder.customer_order_id)
        .group_by(MerchantOrder.customer_order_id)
        .having(func.count(MerchantOrder.id) > 1)
        .subquery()
    )
    multi_tenant_today = (
        db.query(func.count(CustomerOrder.id))
        .filter(CustomerOrder.id.in_(db.query(multi_ids.c.customer_order_id)))
        .filter(CustomerOrder.created_at >= today_start, CustomerOrder.created_at < today_end)
        .scalar()
    )

    total_merchants  = db.query(func.count(Merchant.id)).scalar()
    active_merchants = db.query(func.count(Merchant.id)).filter(Merchant.status == MerchantStatus.ACTIVE).scalar()
    pending_merchants = db.query(func.count(Merchant.id)).filter(Merchant.status == MerchantStatus.PENDING).scalar()

    total_customers = db.query(func.count(Customer.id)).scalar()
    new_customers_today = (
        db.query(func.count(Customer.id))
        .filter(Customer.created_at >= today_start, Customer.created_at < today_end)
        .scalar()
    )

    pw = (
        db.query(
            func.count(Withdrawal.id),
            func.coalesce(func.sum(Withdrawal.amount), 0.0),
        )
        .filter(Withdrawal.status == WithdrawalStatus.PENDING)
        .first()
    )
    pending_withdrawals       = pw[0] or 0
    pending_withdrawal_amount = float(pw[1] or 0.0)

    # ── Pendapatan platform (biaya layanan bersih dari order DONE) ───────────────
    # net = platform_fee − platform_fee_refunded. Diakui saat struk tuntas (DONE),
    # selaras dengan definisi "total transaksi" di atas.
    def _platform_revenue(start=None, end=None) -> float:
        q = (
            db.query(func.coalesce(
                func.sum(CustomerOrder.platform_fee - CustomerOrder.platform_fee_refunded), 0.0
            ))
            .filter(CustomerOrder.status == DONE)
        )
        if start is not None:
            q = q.filter(CustomerOrder.created_at >= start, CustomerOrder.created_at < end)
        return float(q.scalar() or 0.0)

    platform_revenue_today = _platform_revenue(today_start, today_end)
    platform_revenue_total = _platform_revenue()
    fee_setting = fee_svc.get_settings(db)

    # ── Grafik tren 8 hari (transaksi DONE per hari WIB) ─────────────────────────
    rows = (
        db.query(CustomerOrder.created_at, CustomerOrder.total_harga)
        .filter(CustomerOrder.status == DONE)
        .filter(CustomerOrder.created_at >= chart_start, CustomerOrder.created_at < today_end)
        .all()
    )
    buckets: dict = {}
    for created_at, total in rows:
        if created_at is None:
            continue
        d = _to_wib_date(created_at)
        buckets[d] = buckets.get(d, 0.0) + float(total or 0.0)

    today_wib = datetime.now(WIB).date()
    transaksi_chart = [
        {
            "date": (today_wib - timedelta(days=i)).isoformat(),
            "total": float(buckets.get(today_wib - timedelta(days=i), 0.0)),
        }
        for i in range(7, -1, -1)
    ]

    # ── Top 5 tenant minggu ini (nilai transaksi SELESAI) ────────────────────────
    top_rows = (
        db.query(
            Merchant.id,
            Merchant.nama,
            func.coalesce(func.sum(MerchantOrder.total_harga), 0.0).label("total"),
            func.count(MerchantOrder.id).label("orders"),
        )
        .join(MerchantOrder, MerchantOrder.merchant_id == Merchant.id)
        .filter(MerchantOrder.status == MerchantOrderStatus.SELESAI)
        .filter(MerchantOrder.created_at >= week_start)
        .group_by(Merchant.id, Merchant.nama)
        .order_by(func.sum(MerchantOrder.total_harga).desc())
        .limit(5)
        .all()
    )
    top_tenants = [
        {"id": r.id, "nama": r.nama, "total": float(r.total), "orders": r.orders}
        for r in top_rows
    ]

    # ── Transaksi terbaru ────────────────────────────────────────────────────────
    recent = (
        db.query(CustomerOrder)
        .options(
            joinedload(CustomerOrder.customer),
            joinedload(CustomerOrder.metode),
            joinedload(CustomerOrder.merchant_orders).joinedload(MerchantOrder.merchant),
        )
        .order_by(CustomerOrder.created_at.desc())
        .limit(5)
        .all()
    )
    recent_transactions = [
        {
            "id":             o.order_code,
            "tenant":         ", ".join(
                                  mo.merchant.nama for mo in o.merchant_orders if mo.merchant
                              ) or "-",
            "customer":       o.customer_nama or "-",
            "amount":         float(o.total_harga or 0.0),
            "status":         getattr(o.status, "value", o.status),
            "payment_method": o.metode_pembayaran or "-",
            "created_at":     o.created_at.isoformat() if o.created_at else None,
        }
        for o in recent
    ]

    return {
        "transaksi_today":              transaksi_today,
        "transaksi_yesterday":          transaksi_yesterday,
        "orders_today":                 orders_today,
        "multi_tenant_orders_today":    multi_tenant_today,
        "completed_transactions_today": completed_today,
        "active_transactions":          active_transactions,
        "total_merchants":              total_merchants,
        "active_merchants":             active_merchants,
        "pending_merchants":            pending_merchants,
        "total_customers":              total_customers,
        "new_customers_today":          new_customers_today,
        "pending_withdrawals":          pending_withdrawals,
        "pending_withdrawal_amount":    pending_withdrawal_amount,
        "platform_revenue_today":       platform_revenue_today,
        "platform_revenue_total":       platform_revenue_total,
        "platform_fee_rate":            fee_setting.fee_rate,
        "platform_fee_fixed":           fee_setting.fee_fixed,
        "platform_fee_active":          fee_setting.is_active,
        "transaksi_chart":              transaksi_chart,
        "top_tenants":                  top_tenants,
        "recent_transactions":          recent_transactions,
    }


# ── Pantau merchant ───────────────────────────────────────────────────────────

@router.get("/merchants", summary="List semua merchant")
def list_merchants(
    status: Optional[MerchantStatus] = Query(None),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    query = db.query(Merchant).order_by(Merchant.created_at.desc())
    if status:
        query = query.filter(Merchant.status == status)
    return query.offset(offset).limit(limit).all()


@router.put("/merchants/{merchant_id}/status", summary="Ubah status merchant")
def update_merchant_status(
    merchant_id: int,
    status: MerchantStatus,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Admin bisa aktifkan, suspend, atau nonaktifkan merchant."""
    from fastapi import HTTPException
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(404, "Merchant tidak ditemukan")
    merchant.status = status
    db.commit()
    db.refresh(merchant)
    return {"message": f"Status merchant '{merchant.nama}' diubah ke {status}", "id": merchant_id}


# ── Pantau customer ───────────────────────────────────────────────────────────

@router.get("/customers", summary="List semua customer")
def list_customers(
    search: Optional[str] = Query(None, description="Cari nama/email/phone"),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    query = db.query(Customer).order_by(Customer.created_at.desc())
    if search:
        like = f"%{search}%"
        query = query.filter(
            Customer.nama.ilike(like) |
            Customer.email.ilike(like) |
            Customer.phone.ilike(like)
        )
    return query.offset(offset).limit(limit).all()


# ── Kelola kategori produk GLOBAL ─────────────────────────────────────────────

class CategoryIn(BaseModel):
    nama_kategori: str


def _category_with_count(db: Session, cat: Category) -> dict:
    jumlah = (
        db.query(func.count(Product.id))
        .filter(Product.category_id == cat.id)
        .scalar()
    )
    return {"id": cat.id, "nama_kategori": cat.nama_kategori, "jumlah_produk": jumlah or 0}


@router.get("/categories", summary="List kategori produk global + jumlah produk")
def list_all_categories(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    rows = (
        db.query(
            Category.id,
            Category.nama_kategori,
            func.count(Product.id).label("jumlah_produk"),
        )
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id, Category.nama_kategori)
        .order_by(Category.nama_kategori)
        .all()
    )
    return [
        {"id": r.id, "nama_kategori": r.nama_kategori, "jumlah_produk": r.jumlah_produk}
        for r in rows
    ]


@router.post("/categories", status_code=status.HTTP_201_CREATED,
             summary="Tambah kategori produk global")
def create_category(
    data: CategoryIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    nama = data.nama_kategori.strip()
    if not nama:
        raise HTTPException(422, "Nama kategori tidak boleh kosong")
    if db.query(Category).filter(Category.nama_kategori == nama).first():
        raise HTTPException(409, f"Kategori '{nama}' sudah ada")
    cat = Category(nama_kategori=nama)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return _category_with_count(db, cat)


@router.put("/categories/{category_id}", summary="Ubah nama kategori produk global")
def update_category(
    category_id: int,
    data: CategoryIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Kategori tidak ditemukan")
    nama = data.nama_kategori.strip()
    if not nama:
        raise HTTPException(422, "Nama kategori tidak boleh kosong")
    bentrok = db.query(Category).filter(
        Category.nama_kategori == nama,
        Category.id != category_id,
    ).first()
    if bentrok:
        raise HTTPException(409, f"Kategori '{nama}' sudah ada")
    cat.nama_kategori = nama
    db.commit()
    db.refresh(cat)
    return _category_with_count(db, cat)


@router.delete("/categories/{category_id}", summary="Hapus kategori produk global")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Kategori tidak ditemukan")
    # Lepaskan kategori dari produk yang memakainya (jadi tanpa kategori), lalu hapus.
    db.query(Product).filter(Product.category_id == category_id).update(
        {Product.category_id: None}, synchronize_session=False
    )
    nama = cat.nama_kategori
    db.delete(cat)
    db.commit()
    return {"message": f"Kategori '{nama}' berhasil dihapus", "id": category_id}


# ── Pantau semua order ────────────────────────────────────────────────────────

@router.get("/orders", summary="List semua customer order")
def list_all_orders(
    status: Optional[CustomerOrderStatus] = Query(None),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    from sqlalchemy.orm import joinedload
    query = (
        db.query(CustomerOrder)
        .options(joinedload(CustomerOrder.customer))
        .order_by(CustomerOrder.created_at.desc())
    )
    if status:
        query = query.filter(CustomerOrder.status == status)
    return query.offset(offset).limit(limit).all()


# ── Pengumuman / Broadcast ke merchant ────────────────────────────────────────

class AnnouncementIn(BaseModel):
    judul:        str
    pesan:        str
    # 'penting' = masuk kategori Penting di inbox merchant (default, sesuai
    # kebutuhan); 'pengumuman' = kategori Pengumuman biasa.
    tipe:         str = "penting"
    # Target spesifik. None / kosong = broadcast ke SEMUA merchant.
    merchant_ids: Optional[List[int]] = None


@router.post("/announcements", status_code=status.HTTP_201_CREATED,
             summary="Kirim pengumuman ke merchant (kategori Penting/Pengumuman)")
def create_announcement(
    data: AnnouncementIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    judul = data.judul.strip()
    pesan = data.pesan.strip()
    if not judul or not pesan:
        raise HTTPException(422, "Judul dan pesan tidak boleh kosong")

    tipe = NotifikasiTipe.PENGUMUMAN if data.tipe == "pengumuman" else NotifikasiTipe.PENTING

    # Tentukan merchant target.
    query = db.query(Merchant.id)
    if data.merchant_ids:
        query = query.filter(Merchant.id.in_(data.merchant_ids))
    target_ids = [row[0] for row in query.all()]
    if not target_ids:
        raise HTTPException(404, "Tidak ada merchant target yang ditemukan")

    for mid in target_ids:
        db.add(Notification(
            merchant_id       = mid,
            merchant_order_id = None,
            tipe              = tipe,
            judul             = judul,
            pesan             = pesan,
        ))
    db.commit()

    return {
        "message": f"Pengumuman terkirim ke {len(target_ids)} merchant",
        "tipe": tipe.value,
        "terkirim": len(target_ids),
    }


@router.get("/announcements", summary="Riwayat pengumuman yang dikirim admin")
def list_announcements(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Riwayat broadcast — dikelompokkan per (judul, pesan, menit dikirim)
    sehingga satu pengumuman ke banyak merchant tampil sebagai satu baris."""
    rows = (
        db.query(
            Notification.judul,
            Notification.pesan,
            Notification.tipe,
            func.max(Notification.created_at).label("created_at"),
            func.count(Notification.id).label("penerima"),
        )
        .filter(Notification.tipe.in_([NotifikasiTipe.PENGUMUMAN, NotifikasiTipe.PENTING]))
        .group_by(Notification.judul, Notification.pesan, Notification.tipe)
        .order_by(func.max(Notification.created_at).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "judul": r.judul,
            "pesan": r.pesan,
            "tipe": getattr(r.tipe, "value", r.tipe),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "penerima": r.penerima,
        }
        for r in rows
    ]
