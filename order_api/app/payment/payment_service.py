import json
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.customer_order.customer_order_model import CustomerOrder, CustomerOrderStatus
from app.merchant_order.merchant_order_model import MerchantOrderStatus
from app.payment import tripay_client
from app.payment.payment_model import Payment, StatusPembayaran
from app.payment.payment_schema import ChargeResponse, GatewayChannelOut, PaymentCreate
from app.payment_method.payment_method_model import PaymentMethod


# Peta nama metode → tipe tampilan (dipakai mode dummy & metode manual/Tunai).
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


def _payment_type(payment: Payment, metode: PaymentMethod) -> str:
    """Tipe tampilan dari isi record (deterministik untuk dummy maupun Tripay)."""
    if payment.qrcode_kode_url:
        return "qr"
    if payment.va_number:
        return "va"
    if payment.payment_url:
        return "redirect"
    return _resolve_type(metode.nama_metode)


def _build_charge_response(payment: Payment, metode: PaymentMethod) -> ChargeResponse:
    """Bangun respons charge dari record Payment + metode (deterministik)."""
    tipe = _payment_type(payment, metode)
    order = payment.pesanan
    instructions = _INSTRUCTIONS.get(tipe, [])
    if payment.instructions_json:
        try:
            parsed = json.loads(payment.instructions_json)
            if parsed:
                instructions = parsed
        except ValueError:
            pass
    fee = float(payment.fee or 0.0)
    return ChargeResponse(
        payment_id     = payment.id,
        payment_token  = payment.public_token,
        transaction_id = payment.transaction_id,
        status         = payment.status_pembayaran,
        method         = metode.nama_metode,
        type           = tipe,
        gateway        = payment.gateway or "dummy",
        nominal        = payment.nominal,
        fee            = fee,
        subtotal       = payment.nominal - fee,
        qr_string      = payment.qrcode_kode_url if tipe == "qr" else None,
        va_number      = payment.va_number if tipe == "va" else None,
        bank           = metode.nama_metode if tipe == "va" else None,
        payment_url    = payment.payment_url if tipe == "redirect" else None,
        expires_at     = payment.expires_at,
        instructions   = instructions,
        order_id       = payment.id_pesanan,
        order_code     = order.order_code if order else "",
        no_meja        = order.no_meja if order else None,
        created_at     = payment.timestamp,
    )


def _charge_dummy(payment: Payment, order: CustomerOrder, tipe: str) -> None:
    """Isi field gateway ala dummy (tanpa uang asli)."""
    payment.transaction_id = f"DUMMY-{order.order_code}-{payment.id}"
    if tipe == "qr":
        payment.qrcode_kode_url = f"DUMMYQR|{payment.transaction_id}|{payment.nominal:.0f}"
    elif tipe == "va":
        payment.va_number = f"8808{payment.id:010d}"
    elif tipe == "redirect":
        base = settings.frontend_url.rstrip("/")
        payment.payment_url = f"{base}/payment/status/{payment.public_token}"


def _charge_tripay(payment: Payment, order: CustomerOrder, metode: PaymentMethod) -> None:
    """Buat transaksi asli di Tripay & petakan responsnya ke record Payment.

    Fee channel dibebankan ke customer: atur "Biaya Ditanggung" = Customer per
    channel di dashboard Tripay. Tripay lalu menagih (amount + fee_customer);
    kita simpan fee itu di payment.fee dan nominal = amount + fee agar tampilan
    FE sama dengan yang benar-benar ditagih.
    """
    if not tripay_client.is_configured():
        raise HTTPException(503, "Gateway Tripay belum dikonfigurasi (kredensial kosong)")
    if not metode.tripay_code:
        raise HTTPException(400, f"Metode '{metode.nama_metode}' belum terhubung ke channel Tripay")

    amount = int(round(float(order.total_harga or 0.0)))
    if amount <= 0:
        raise HTTPException(400, "Nominal pesanan tidak valid")

    # Expired Tripay disinkronkan dengan timeout bayar order (config.py).
    pay_secs = settings.customer_pay_timeout_seconds
    expired_time = int(time.time()) + (pay_secs if pay_secs > 0 else 24 * 3600)

    merchant_ref = f"{order.order_code}-{payment.id}"
    customer = order.customer
    api_base = settings.static_base_url.rstrip("/")
    fe_base = settings.frontend_url.rstrip("/")

    data = tripay_client.create_transaction(
        method         = metode.tripay_code,
        merchant_ref   = merchant_ref,
        amount         = amount,
        customer_name  = (customer.nama if customer else None) or "Customer Teras LA",
        customer_email = (customer.email if customer else None) or "customer@terasla.id",
        customer_phone = customer.phone if customer else None,
        order_items    = [{"name": f"Pesanan {order.order_code}", "price": amount, "quantity": 1}],
        expired_time   = expired_time,
        callback_url   = f"{api_base}/payments/webhook/tripay",
        return_url     = f"{fe_base}/payment/status/{payment.public_token}",
    )

    fee_customer = float(data.get("fee_customer") or 0)
    payment.gateway         = "tripay"
    payment.transaction_id  = data.get("reference")
    payment.fee             = fee_customer
    payment.nominal         = float(amount) + fee_customer  # total yang ditagih ke customer
    payment.qrcode_kode_url = data.get("qr_string")
    payment.va_number       = data.get("pay_code")
    payment.payment_url     = data.get("checkout_url")
    if data.get("expired_time"):
        payment.expires_at = datetime.fromtimestamp(int(data["expired_time"]), tz=timezone.utc)
    instructions = tripay_client.flatten_instructions(data.get("instructions"))
    if instructions:
        payment.instructions_json = json.dumps(instructions, ensure_ascii=False)


def charge(db: Session, id_pesanan: int, metode_pembayaran_id: int) -> ChargeResponse:
    """Buat transaksi pembayaran untuk sebuah order.

    PAYMENT_GATEWAY=dummy  → transaksi simulasi (auto-settle / simulate-paid).
    PAYMENT_GATEWAY=tripay → transaksi asli di Tripay; status berubah lewat
    webhook (+ rekonsiliasi polling). Tunai selalu lokal (settle di kasir).
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
    use_tripay = settings.payment_gateway.lower() == "tripay" and tipe != "manual"

    payment = Payment(
        id_pesanan        = id_pesanan,
        metode_pembayaran_id = metode.id,
        metode_pembayaran = metode.nama_metode,
        nominal           = float(order.total_harga or 0.0),
        status_pembayaran = StatusPembayaran.PENDING,
        gateway           = "tripay" if use_tripay else "dummy",
        expires_at        = datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(payment)
    db.flush()  # butuh payment.id untuk merchant_ref / nomor deterministik

    if use_tripay:
        try:
            _charge_tripay(payment, order, metode)
        except Exception:
            # Jangan tinggalkan payment PENDING yatim bila Tripay gagal.
            db.rollback()
            raise
    else:
        _charge_dummy(payment, order, tipe)

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

    Pengganti webhook gateway untuk demo. HANYA aktif saat PAYMENT_GATEWAY=dummy
    dan hanya untuk payment yang dibuat gateway dummy; nonaktif juga bila
    settings.dummy_payment_auto_paid_seconds <= 0.
    """
    if settings.payment_gateway.lower() != "dummy":
        return
    if payment.gateway and payment.gateway != "dummy":
        return
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


# Throttle rekonsiliasi aktif ke Tripay per payment (in-memory, cukup untuk
# deployment single-process). FE polling tiap 3 dtk; kita cek ke Tripay maks
# 1x per interval ini agar tidak membanjiri API mereka.
_TRIPAY_RECONCILE_INTERVAL = 15.0  # detik
_tripay_last_check: dict[int, float] = {}


def _apply_tripay_status(db: Session, payment: Payment, status: str) -> None:
    """Terapkan status transaksi Tripay ke record Payment (idempotent)."""
    status = (status or "").upper()
    if status == "PAID":
        _settle_payment(payment)
        db.commit()
        db.refresh(payment)
    elif status in ("EXPIRED", "FAILED", "REFUND"):
        if payment.status_pembayaran == StatusPembayaran.PENDING:
            payment.status_pembayaran = StatusPembayaran.GAGAL
            db.commit()
            db.refresh(payment)


def _reconcile_tripay_if_needed(db: Session, payment: Payment) -> None:
    """Cek aktif status transaksi ke Tripay saat masih PENDING.

    Jaring pengaman bila webhook gagal/terlambat — dipicu polling status FE,
    di-throttle agar tidak tiap 3 detik memukul API Tripay.
    """
    if (
        payment.gateway != "tripay"
        or payment.status_pembayaran != StatusPembayaran.PENDING
        or not payment.transaction_id
        or not tripay_client.is_configured()
    ):
        return
    now = time.monotonic()
    last = _tripay_last_check.get(payment.id, 0.0)
    if now - last < _TRIPAY_RECONCILE_INTERVAL:
        return
    _tripay_last_check[payment.id] = now
    try:
        data = tripay_client.get_transaction(payment.transaction_id)
    except Exception:
        return  # Tripay tidak bisa dihubungi → biarkan, webhook/percobaan berikut
    _apply_tripay_status(db, payment, data.get("status"))
    if payment.status_pembayaran != StatusPembayaran.PENDING:
        _tripay_last_check.pop(payment.id, None)


def get_payment_by_token_or_404(db: Session, token: str) -> Payment:
    p = db.query(Payment).filter(Payment.public_token == token).first()
    if not p:
        raise HTTPException(404, "Pembayaran tidak ditemukan")
    return p


def get_charge_status(db: Session, token: str) -> ChargeResponse:
    payment = get_payment_by_token_or_404(db, token)
    _auto_settle_if_due(db, payment)
    _reconcile_tripay_if_needed(db, payment)
    metode = db.query(PaymentMethod).filter(PaymentMethod.id == payment.metode_pembayaran_id).first()
    if not metode:
        # Metode mungkin sudah dihapus; tetap kembalikan info seadanya.
        metode = PaymentMethod(id=payment.metode_pembayaran_id or 0, nama_metode=payment.metode_pembayaran)
    return _build_charge_response(payment, metode)


def simulate_paid(db: Session, token: str) -> ChargeResponse:
    """Pengganti webhook gateway — HANYA tersedia saat PAYMENT_GATEWAY=dummy."""
    if settings.payment_gateway.lower() != "dummy":
        raise HTTPException(403, "Simulasi pembayaran hanya tersedia di mode dummy")
    payment = get_payment_by_token_or_404(db, token)
    if payment.gateway and payment.gateway != "dummy":
        raise HTTPException(403, "Pembayaran ini dibuat lewat gateway asli — tidak bisa disimulasikan")
    _settle_payment(payment)
    db.commit()
    db.refresh(payment)
    metode = db.query(PaymentMethod).filter(PaymentMethod.id == payment.metode_pembayaran_id).first()
    if not metode:
        metode = PaymentMethod(id=payment.metode_pembayaran_id or 0, nama_metode=payment.metode_pembayaran)
    return _build_charge_response(payment, metode)


def process_tripay_callback(db: Session, raw_body: bytes, signature: str, event: str) -> dict:
    """Proses webhook Tripay (event payment_status).

    Verifikasi HMAC-SHA256(private_key, raw body) di header X-Callback-Signature
    SEBELUM body dipercaya. PAID → settle (idempotent); EXPIRED/FAILED → GAGAL.
    Respons {"success": true} = Tripay berhenti mengulang kiriman.
    """
    if not tripay_client.is_configured():
        raise HTTPException(503, "Gateway Tripay belum dikonfigurasi")
    if not tripay_client.verify_callback_signature(raw_body, signature):
        raise HTTPException(401, "Signature callback tidak valid")
    if event and event != "payment_status":
        return {"success": True}  # event lain: acknowledge saja

    try:
        data = json.loads(raw_body)
    except ValueError:
        raise HTTPException(400, "Body callback bukan JSON valid")

    reference = data.get("reference")
    payment = db.query(Payment).filter(Payment.transaction_id == reference).first()
    if not payment:
        raise HTTPException(404, f"Pembayaran dengan reference '{reference}' tidak ditemukan")

    _apply_tripay_status(db, payment, data.get("status"))
    return {"success": True}


# Cache daftar channel Tripay (module-level; hemat kuota API, FE boleh sering fetch).
_CHANNELS_CACHE_TTL = 300.0  # detik
_channels_cache: dict = {"ts": 0.0, "data": []}


def list_gateway_channels() -> List[GatewayChannelOut]:
    """Daftar channel Tripay aktif + struktur fee (untuk ditampilkan ke customer).

    Mode dummy / kredensial kosong → list kosong (FE tampilkan 'tanpa biaya').
    """
    if settings.payment_gateway.lower() != "tripay" or not tripay_client.is_configured():
        return []
    now = time.monotonic()
    if now - _channels_cache["ts"] < _CHANNELS_CACHE_TTL:
        return _channels_cache["data"]
    try:
        raw = tripay_client.get_payment_channels()
    except Exception:
        return _channels_cache["data"]  # gagal fetch → pakai cache lama (bisa kosong)
    channels = []
    for ch in raw:
        fee_cust = ch.get("fee_customer") or {}
        channels.append(GatewayChannelOut(
            code        = ch.get("code", ""),
            name        = ch.get("name", ""),
            group       = ch.get("group"),
            active      = bool(ch.get("active", True)),
            fee_flat    = float(fee_cust.get("flat") or 0),
            fee_percent = float(fee_cust.get("percent") or 0),
            minimum_fee = ch.get("minimum_fee"),
            maximum_fee = ch.get("maximum_fee"),
        ))
    _channels_cache["ts"] = now
    _channels_cache["data"] = channels
    return channels


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