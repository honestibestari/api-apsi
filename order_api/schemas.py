from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CategoryEnum(str, Enum):
    makanan = "makanan"
    minuman = "minuman"

class StatusEnum(str, Enum):
    pending = "pending"
    diproses = "diproses"
    selesai = "selesai"
    dibatalkan = "dibatalkan"

# ─── MenuItem Schemas ────────────────────────────────
class MenuItemBase(BaseModel):
    nama: str
    kategori: CategoryEnum
    harga: float
    deskripsi: Optional[str] = None
    tersedia: bool = True

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemResponse(MenuItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ─── OrderItem Schemas ───────────────────────────────
class OrderItemBase(BaseModel):
    menu_item_id: int
    jumlah: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    jumlah: int
    harga_satuan: float
    subtotal: float
    menu_item: MenuItemResponse

    class Config:
        from_attributes = True

# ─── Order Schemas ───────────────────────────────────
class OrderBase(BaseModel):
    nama_pelanggan: str
    nomor_meja: int
    catatan: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdateStatus(BaseModel):
    status: StatusEnum

class OrderResponse(OrderBase):
    id: int
    status: StatusEnum
    total_harga: float
    created_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True

class OrderSummary(BaseModel):
    id: int
    nama_pelanggan: str
    nomor_meja: int
    status: StatusEnum
    total_harga: float
    created_at: datetime
    jumlah_item: int

    class Config:
        from_attributes = True