from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.customer_order.customer_order_model import TipeOrder
from app.merchant_order.merchant_order_model import MerchantOrderStatus, NotifikasiTipe


# ── Embedded ────────────────────────────────────────────────────────────────────

class ProductInfo(BaseModel):
    id:    int
    nama:  str
    harga: float

    model_config = ConfigDict(from_attributes=True)


class OrderItemOut(BaseModel):
    id:           int
    jumlah:       int
    harga_satuan: float
    subtotal:     float
    varian:       Optional[str] = None
    product:      Optional[ProductInfo] = None

    model_config = ConfigDict(from_attributes=True)


# ── Output ─────────────────────────────────────────────────────────────────────

class MerchantOrderOut(BaseModel):
    id:                int
    order_code:        str
    customer_order_id: int
    merchant_id:       int
    merchant_nama:     Optional[str] = None
    status:            MerchantOrderStatus
    subtotal:          float
    biaya_penanganan:  float
    total_harga:       float
    tipe_order:        Optional[TipeOrder] = None
    no_meja:           Optional[str] = None
    pelanggan_nama:    Optional[str] = None
    metode_pembayaran: Optional[str] = None
    items:             List[OrderItemOut] = []
    created_at:        datetime
    updated_at:        Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MerchantOrderSummary(BaseModel):
    id:             int
    order_code:     str
    merchant_id:    int
    status:         MerchantOrderStatus
    total_harga:    float
    pelanggan_nama: Optional[str] = None
    metode_pembayaran: Optional[str] = None
    no_meja:        Optional[str] = None
    preview_items:  Optional[str] = None
    created_at:     datetime

    model_config = ConfigDict(from_attributes=True)


class MerchantOrderStatusUpdate(BaseModel):
    status: MerchantOrderStatus


# ── Notifikasi ────────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id:                int
    merchant_order_id: Optional[int]
    tipe:              NotifikasiTipe
    judul:             str
    pesan:             str
    is_read:           bool
    created_at:        datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationMarkRead(BaseModel):
    ids: List[int]
