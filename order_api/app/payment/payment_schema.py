from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.payment.payment_model import StatusPembayaran


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
    struk_dikirim:        Optional[str]    = None
    timestamp:            datetime
    model_config = ConfigDict(from_attributes=True)