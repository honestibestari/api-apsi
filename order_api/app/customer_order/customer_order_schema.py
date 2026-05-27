from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.customer_order.customer_order_model import (
    CustomerOrderStatus,
    MetodePembayaran,
    TipeOrder,
)
from app.merchant_order.merchant_order_model import MerchantOrderStatus


# ── Input ──────────────────────────────────────────────────────────────────────

class CustomerInfo(BaseModel):
    nama: str
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("nama")
    @classmethod
    def nama_tidak_kosong(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama pelanggan tidak boleh kosong")
        return v


class ItemCreate(BaseModel):
    product_id: int
    jumlah:     int = 1
    varian:     Optional[str] = None

    @field_validator("jumlah")
    @classmethod
    def jumlah_positif(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Jumlah harus minimal 1")
        return v


class CustomerOrderCreate(BaseModel):
    customer:          CustomerInfo
    dining_table_code: Optional[str]   = None
    tipe_order:        TipeOrder        = TipeOrder.DINE_IN
    metode_pembayaran: MetodePembayaran = MetodePembayaran.QRIS
    catatan:           Optional[str]   = None
    items:             List[ItemCreate]

    @field_validator("items")
    @classmethod
    def minimal_satu_item(cls, v: List[ItemCreate]) -> List[ItemCreate]:
        if not v:
            raise ValueError("Order harus berisi minimal 1 item")
        return v

    @model_validator(mode="after")
    def dine_in_butuh_meja(self) -> "CustomerOrderCreate":
        if self.tipe_order == TipeOrder.DINE_IN and not self.dining_table_code:
            raise ValueError("dining_table_code wajib diisi untuk tipe dine_in")
        return self


# ── Output ─────────────────────────────────────────────────────────────────────

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


class CustomerBrief(BaseModel):
    id:    int
    nama:  str
    email: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MerchantOrderNested(BaseModel):
    """Bagian per-tenant di dalam detail customer order."""
    id:            int
    order_code:    str
    merchant_id:   int
    merchant_nama: Optional[str] = None
    status:        MerchantOrderStatus
    subtotal:      float
    total_harga:   float
    items:         List[OrderItemOut] = []

    model_config = ConfigDict(from_attributes=True)


class CustomerOrderOut(BaseModel):
    id:                int
    order_code:        str
    status:            CustomerOrderStatus
    tipe_order:        TipeOrder
    metode_pembayaran: MetodePembayaran
    catatan:           Optional[str] = None
    total_harga:       float
    no_meja:           Optional[str] = None
    tenant_count:      int
    created_at:        datetime
    updated_at:        Optional[datetime] = None
    customer:          CustomerBrief
    merchant_orders:   List[MerchantOrderNested] = []

    model_config = ConfigDict(from_attributes=True)


class CustomerOrderSummary(BaseModel):
    id:                int
    order_code:        str
    status:            CustomerOrderStatus
    metode_pembayaran: MetodePembayaran
    total_harga:       float
    tenant_count:      int
    no_meja:           Optional[str] = None
    customer_nama:     Optional[str] = None
    created_at:        datetime

    model_config = ConfigDict(from_attributes=True)
