from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.customer_order.customer_order_model import CustomerOrder, CustomerOrderStatus
from app.merchant_order.merchant_order_model import MerchantOrderStatus
from app.payment.payment_model import Payment, StatusPembayaran
from app.payment.payment_schema import ChargeResponse, PaymentCreate
from app.payment_method.payment_method_model import PaymentMethod


# ── Dummy gateway ───────────────────────────────────────────────────────────
# Peta nama metode → tipe tampilan. Saat pakai gateway asli, `type` ini diambil
# dari payment_type gateway (mis. Midtrans), bukan dari sini.
def _resolve_type(nama_metode: str) -> str:
    n = (nama_metode or "").lower()
    if "qris" in n:
        return "qr"
    if "tunai" in n or "cash" in n:
        return "manual"
    if "va" in n or "virtual" in n or "transfer" in n or "bank" in n:
        return "va"
    if "gopay" in n or "ovo" in n or "dana" in n or "shopee" in n:
        return "redirect"
    return "manual"


_INSTRUCTIONS = {
    "qr":       ["Buka aplikasi e-wallet / m-banking", "Pindai QR di layar", "Konfirmasi pembayaran"],
    "va":       ["Buka m-banking / ATM", "Pilih Transfer ke Virtual Account", "Masukkan nomor VA", "Konfirmasi"],
    "redirect": ["Anda akan diarahkan ke halaman pembayaran", "Selesaikan pembayaran di sana"],
    "manual":   ["Tunjukkan kode pesanan ke kasir", "Bayar tunai saat pesanan diantar"],
}


def _build_charge_response(payment: Payment, metode: PaymentMethod) -> ChargeResponse:
    """Bangun respons charge dari record Payment + metode (deterministik)."""
    tipe = _resolve_type(metode.nama_metode)
    order = payment.pesanan
    return ChargeResponse(
        payment_id     = payment.id,
        payment_token  = payment.public_token,
        transaction_id = payment.transaction_id,
        status         = payment.status_pembayaran,
        method         = metode.nama_metode,
        type           = tipe,
        nominal        = payment.nominal,
        qr_string      = payment.qrcode_kode_url if tipe == "qr" else None,
        va_number      = payment.va_number if tipe == "va" else None,
        bank           = metode.nama_metode if tipe == "va" else None,
        payment_url    = payment.payment_url if tipe == "redirect" else None,
        expires_at     = payment.expires_at,
        instructions   = _INSTRUCTIONS.get(tipe, []),
        order_id       = payment.id_pesanan,
        order_code     = order.order_code if order else "",
        no_meja        = order.no_meja if order else None,
        created_at     = payment.timestamp,
    )


def charge(db: Session, id_pesanan: int, metode_pembayaran_id: int) -> ChargeResponse:
    """Buat 'transaksi pembayaran' dummy untuk sebuah order.

    Meniru alur gateway: kembalikan instruksi sesuai tipe metode. Belum benar-benar
    membayar — status awal PENDING; gunakan simulate_paid() (pengganti webhook).
    """
    order = db.query(CustomerOrder).filter(CustomerOrder.id == id_pesanan).first()
    if not order:
        raise HTTPException(404, "Pesanan tidak ditemukan")

    metode = db.query(PaymentMethod).filter(PaymentMethod.id == metode_pembayaran_id).first()
    if not metode:
        raise HTTPException(404, "Metode pembayaran tidak ditemukan")
    if not metode.is_active:
        raise HTTPException(400, f"Metode '{metode.nama_metode}' sedang tidak aktif")

    existing = db.query(Payment).filter(
        Payment.id_pesanan == id_pesanan,
        Payment.status_pembayaran == StatusPembayaran.LUNAS,
    ).first()
    if existing:
        raise HTTPException(400, "Pesanan ini sudah lunas")

    tipe = _resolve_type(metode.nama_metode)

    payment = Payment(
        id_pesanan        = id_pesanan,
        metode_pembayaran_id = metode.id,
        metode_pembayaran = metode.nama_metode,
        nominal           = float(order.total_harga or 0.0),
        status_pembayaran = StatusPembayaran.PENDING,
        expires_at        = datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(payment)
    db.flush()  # butuh payment.id untuk membentuk nomor/id deterministik

    payment.transaction_id = f"DUMMY-{order.order_code}-{payment.id}"
    if tipe == "qr":
        payment.qrcode_kode_url = f"DUMMYQR|{payment.transaction_id}|{payment.nominal:.0f}"
    elif tipe == "va":
        payment.va_number = f"8808{payment.id:010d}"
    elif tipe == "redirect":
        base = settings.frontend_url.rstrip("/")
        payment.payment_url = f"{base}/payment/status/{payment.public_token}"

    # Jaga konsistensi: metode terpilih juga tercatat di order.
    order.metode_pembayaran_id = metode.id

    # Tunai (type=manual) tidak lewat gateway → langsung dianggap selesai
    # (dibayar di kasir). FE langsung ke layar sukses.
    if tipe == "manual":
        _settle_payment(payment)

    db.commit()
    db.refresh(payment)
    return _build_charge_response(payment, metode)


def _settle_payment(payment: Payment) -> None:
    """Tandai pembayaran LUNAS + SINKRONKAN kedua dokumen order. Idempotent.

    Saat pembayaran selesai:
      • CustomerOrder: verifying → open
      • tiap MerchantOrder yang masih 'baru' → 'terbuka' (open), siap di-confirm/
        tolak oleh merchant.
    Tidak commit — pemanggil yang commit.
    """
    if payment.status_pembayaran == StatusPembayaran.LUNAS:
        return
    payment.status_pembayaran = StatusPembayaran.LUNAS
    payment.paid_at = datetime.now(timezone.utc)

    order = payment.pesanan
    if not order:
        return
    if order.status == CustomerOrderStatus.VERIFYING:
        order.status = CustomerOrderStatus.OPEN
    for mo in order.merchant_orders:
        if mo.status == MerchantOrderStatus.BARU:
            mo.status = MerchantOrderStatus.TERBUKA
    # Catatan: stok TIDAK dikurangi di sini — sudah dikonsumsi saat order dibuat
    # (di-reserve) dan dikembalikan saat dibatalkan.


def _auto_settle_if_due(db: Session, payment: Payment) -> None:
    """Mode dummy: auto-LUNAS bila pembayaran PENDING sudah lewat ambang detik.

    Pengganti webhook gateway untuk demo. Nonaktif bila
    settings.dummy_payment_auto_paid_seconds <= 0 (mis. saat gateway asli aktif).
    """
    secs = settings.dummy_payment_auto_paid_seconds
    if secs <= 0 or payment.status_pembayaran != StatusPembayaran.PENDING:
        return
    created = payment.timestamp
    if not created:
        return
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if (datetime.now(timezone.utc) - created).total_seconds() < secs:
        return
    _settle_payment(payment)
    db.commit()
    db.refresh(payment)


def get_payment_by_token_or_404(db: Session, token: str) -> Payment:
    p = db.query(Payment).filter(Payment.public_token == token).first()
    if not p:
        raise HTTPException(404, "Pembayaran tidak ditemukan")
    return p


def get_charge_status(db: Session, token: str) -> ChargeResponse:
    payment = get_payment_by_token_or_404(db, token)
    _auto_settle_if_due(db, payment)
    metode = db.query(PaymentMethod).filter(PaymentMethod.id == payment.metode_pembayaran_id).first()
    if not metode:
        # Metode mungkin sudah dihapus; tetap kembalikan info seadanya.
        metode = PaymentMethod(id=payment.metode_pembayaran_id or 0, nama_metode=payment.metode_pembayaran)
    return _build_charge_response(payment, metode)


def simulate_paid(db: Session, token: str) -> ChargeResponse:
    """Pengganti webhook gateway: tandai pembayaran LUNAS & sinkronkan order."""
    payment = get_payment_by_token_or_404(db, token)
    _settle_payment(payment)
    db.commit()
    db.refresh(payment)
    metode = db.query(PaymentMethod).filter(PaymentMethod.id == payment.metode_pembayaran_id).first()
    if not metode:
        metode = PaymentMethod(id=payment.metode_pembayaran_id or 0, nama_metode=payment.metode_pembayaran)
    return _build_charge_response(payment, metode)


def get_payment_or_404(db: Session, payment_id: int) -> Payment:
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(404, "Pembayaran tidak ditemukan")
    return p


def list_payments(db: Session, id_pesanan: Optional[int] = None) -> List[Payment]:
    query = db.query(Payment).order_by(Payment.timestamp.desc())
    if id_pesanan:
        query = query.filter(Payment.id_pesanan == id_pesanan)
    return query.all()


def create_payment(db: Session, data: PaymentCreate) -> Payment:
    # Cek apakah sudah ada payment LUNAS untuk pesanan ini
    existing = db.query(Payment).filter(
        Payment.id_pesanan == data.id_pesanan,
        Payment.status_pembayaran == StatusPembayaran.LUNAS
    ).first()
    if existing:
        raise HTTPException(400, "Pesanan ini sudah lunas")

    payment = Payment(
        id_pesanan        = data.id_pesanan,
        metode_pembayaran = data.metode_pembayaran,
        nominal           = data.nominal,
        qrcode_kode_url   = data.qrcode_kode_url,
        status_pembayaran = StatusPembayaran.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def update_payment_status(db: Session, payment_id: int, status: StatusPembayaran) -> Payment:
    payment = get_payment_or_404(db, payment_id)
    payment.status_pembayaran = status
    db.commit()
    db.refresh(payment)
    return payment