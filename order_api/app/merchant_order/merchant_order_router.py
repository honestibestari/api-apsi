import urllib.parse
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.merchant_order import merchant_order_service
from app.merchant_order.merchant_order_model import MerchantOrderStatus
from app.core.auth import get_current_merchant
from app.merchant.merchant_model import Merchant
from app.merchant_order.merchant_order_schema import (
    MerchantDashboardSummary,
    MerchantOrderOut,
    MerchantOrderStatusUpdate,
    MerchantOrderSummary,
    NotificationMarkRead,
    NotificationOut,
)

router = APIRouter(prefix="/merchant-orders", tags=["Merchant Orders"])


def _ensure_self(merchant_id: int, current_merchant: Merchant) -> None:
    """Cegah IDOR: merchant hanya boleh mengakses data miliknya sendiri.

    Endpoint notifikasi menerima merchant_id di path; pastikan ia sama dengan
    merchant pemilik token, bukan milik merchant lain.
    """
    if merchant_id != current_merchant.id:
        raise HTTPException(status_code=403, detail="Tidak boleh mengakses data merchant lain")


@router.get(
    "",
    response_model=List[MerchantOrderSummary],
    summary="[Merchant] List pesanan masuk",
)
def list_merchant_orders(
    merchant_id: Optional[int]                 = Query(None, description="Filter per merchant"),
    status:      Optional[MerchantOrderStatus] = Query(None, description="baru | terbuka | diproses | selesai | dibatalkan"),
    offset:      int                           = Query(0, ge=0),
    limit:       int                           = Query(50, ge=1, le=200),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return merchant_order_service.list_merchant_orders(
        db, merchant_id=current_merchant.id  
    )


@router.get(
    "/summary",
    response_model=MerchantDashboardSummary,
    summary="[Merchant] Ringkasan keuangan (dashboard Kontrol)",
)
def merchant_dashboard_summary(
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return merchant_order_service.get_dashboard_summary(db, current_merchant)


@router.get(
    "/report",
    summary="[Merchant] Unduh laporan penjualan (Excel: mingguan/bulanan/tahunan)",
)
def download_sales_report(
    period: str = Query("weekly", description="weekly | monthly | yearly"),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Hasilkan file Excel laporan penjualan merchant untuk periode terpilih."""
    content, filename = merchant_order_service.build_sales_report(db, current_merchant, period)
    # RFC 5987: dukung nama file aman di header Content-Disposition.
    quoted = urllib.parse.quote(filename)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quoted}",
        },
    )


@router.get(
    "/{order_id}",
    response_model=MerchantOrderOut,
    summary="[Merchant] Detail pesanan",
)
def get_merchant_order(order_id: int, db: Session = Depends(get_db)):
    return merchant_order_service.get_merchant_order_or_404(db, order_id)


@router.put(
    "/{order_id}/status",
    response_model=MerchantOrderOut,
    summary="[Merchant] Update status pesanan (sinkron ke customer order)",
)
def update_merchant_order_status(
    order_id: int,
    data: MerchantOrderStatusUpdate,
    db: Session = Depends(get_db),
):
    return merchant_order_service.update_status(db, order_id, data)


# ── Notifikasi ────────────────────────────────────────────────────────────────

@router.get(
    "/notifications/{merchant_id}",
    response_model=List[NotificationOut],
    summary="[Merchant] List inbox notifikasi",
)
def list_notifications(
    merchant_id: int,
    only_unread: bool = Query(False, description="true = belum dibaca saja"),
    offset:      int  = Query(0, ge=0),
    limit:       int  = Query(50, ge=1, le=100),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    _ensure_self(merchant_id, current_merchant)
    return merchant_order_service.list_notifications(
        db, merchant_id, only_unread=only_unread, offset=offset, limit=limit
    )


@router.post(
    "/notifications/{merchant_id}/read",
    summary="[Merchant] Tandai notifikasi tertentu sudah dibaca",
)
def mark_read(
    merchant_id: int,
    data: NotificationMarkRead,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    _ensure_self(merchant_id, current_merchant)
    return merchant_order_service.mark_notifications_read(db, merchant_id, data)


@router.post(
    "/notifications/{merchant_id}/read-all",
    summary="[Merchant] Tandai semua notifikasi sudah dibaca",
)
def mark_all_read(
    merchant_id: int,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    _ensure_self(merchant_id, current_merchant)
    return merchant_order_service.mark_all_notifications_read(db, merchant_id)
