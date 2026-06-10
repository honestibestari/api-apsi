from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.payment.payment_model import StatusPembayaran


# ── Gateway-style charge (dummy sekarang, kontraknya meniru Midtrans/Flip) ──────

class ChargeRequest(BaseModel):
    id_pesanan:           int
    metode_pembayaran_id: int


class ChargeResponse(BaseModel):
    """Respons charge — bentuk diskriminatif: FE render berdasarkan `type`.

    type:
      - "qr"       → tampilkan `qr_string`
      - "va"       → tampilkan `va_number` (+ `bank`)
      - "redirect" → arahkan ke `payment_url`
      - "manual"   → cukup `instructions` (mis. bayar di kasir)
    """
    payment_id:     int
    transaction_id: str
    status:         StatusPembayaran
    method:         str                  # nama metode (mis. "QRIS", "BCA")
    type:           str                  # qr | va | redirect | manual
    nominal:        float
    qr_string:      Optional[str] = None
    va_number:      Optional[str] = None
    bank:           Optional[str] = None
    payment_url:    Optional[str] = None
    expires_at:     Optional[datetime] = None
    instructions:   List[str] = []
    # Info order (untuk layar sukses)
    order_id:       int
    order_code:     str
    no_meja:        Optional[str] = None
    created_at:     Optional[datetime] = None


class PaymentCreate(BaseModel):
    id_pesanan:           int
    metode_pembayaran:    str            
    metode_pembayaran_id: Optional[int] = None 
    nominal:              float
    qrcode_kode_url:      Optional[str] = None


class PaymentMethodInfo(BaseModel):
    id:          int
    nama_metode: str
    model_config = ConfigDict(from_attributes=True)


class PaymentOut(BaseModel):
    id:                   int
    id_pesanan:           int
    metode_pembayaran:    str
    metode_pembayaran_id: Optional[int]    = None  
    metode:               Optional[PaymentMethodInfo] = None 
    status_pembayaran:    StatusPembayaran
    nominal:              float
    qrcode_kode_url:      Optional[str]    = None
    timestamp:            datetime
    model_config = ConfigDict(from_attributes=True)