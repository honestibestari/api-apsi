from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.order.order_model import (
    MetodePembayaran,
    NotifikasiTipe,
    OrderStatus,
    TipeOrder,
)


# ── Embedded product info di dalam item response ──────────────────────────────

class ProductInfo(BaseModel):
    id:        int
    nama:      str
    harga:     float
    deskripsi: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── OrderItem ─────────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: int
    jumlah:     int = 1
    varian:     Optional[str] = None

    @field_validator("jumlah")
    @classmethod
    def jumlah_positif(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Jumlah harus minimal 1")
        return v


class OrderItemOut(BaseModel):
    id:           int
    jumlah:       int
    harga_satuan: float
    subtotal:     float
    varian:       Optional[str]
    product:      Optional[ProductInfo] = None

    model_config = ConfigDict(from_attributes=True)


# ── Order Create ──────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    merchant_id:       int
    nama_pelanggan:    str
    tipe_order:        TipeOrder        = TipeOrder.DINE_IN
    dining_table_code: Optional[str]   = None
    catatan:           Optional[str]   = None
    metode_pembayaran: MetodePembayaran = MetodePembayaran.QRIS
    items:             List[OrderItemCreate]

    @field_validator("nama_pelanggan")
    @classmethod
    def nama_tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama pelanggan tidak boleh kosong")
        return v

    @field_validator("items")
    @classmethod
    def minimal_satu_item(cls, v: List[OrderItemCreate]) -> List[OrderItemCreate]:
        if not v:
            raise ValueError("Order harus berisi minimal 1 item")
        return v

    @model_validator(mode="after")
    def dine_in_butuh_meja(self) -> "OrderCreate":
        if self.tipe_order == TipeOrder.DINE_IN and not self.dining_table_code:
            raise ValueError("dining_table_code wajib diisi untuk tipe dine_in")
        return self


# ── Order Status Update ───────────────────────────────────────────────────────

class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ── Order Out ─────────────────────────────────────────────────────────────────

class OrderOut(BaseModel):
    id:                int
    order_code:        str
    merchant_id:       int
    dining_table_id:   Optional[int]
    no_meja:           Optional[str]    = None
    nama_pelanggan:    str
    tipe_order:        TipeOrder
    status:            OrderStatus
    catatan:           Optional[str]
    subtotal:          float
    biaya_penanganan:  float
    total_harga:       float
    metode_pembayaran: MetodePembayaran
    items:             List[OrderItemOut] = []
    created_at:        datetime
    updated_at:        Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ── Order Summary (untuk list) ────────────────────────────────────────────────

class OrderSummary(BaseModel):
    id:             int
    order_code:     str
    merchant_id:    int
    nama_pelanggan: str
    tipe_order:     TipeOrder
    status:         OrderStatus
    total_harga:    float
    created_at:     datetime
    preview_items:  Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Notifikasi ────────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id:         int
    order_id:   Optional[int]
    tipe:       NotifikasiTipe
    judul:      str
    pesan:      str
    is_read:    bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationMarkRead(BaseModel):
    ids: List[int]


# ── Dashboard Stats ───────────────────────────────────────────────────────────

class OrderStats(BaseModel):
    pesanan_baru:            int
    pesanan_diproses:        int
    pendapatan_hari_ini:     float
    notifikasi_belum_dibaca: int