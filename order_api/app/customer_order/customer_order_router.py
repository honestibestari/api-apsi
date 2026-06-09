from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.customer_order import customer_order_service
from app.customer_order.customer_order_model import CustomerOrderStatus
from app.customer_order.customer_order_schema import (
    CustomerOrderCreate,
    CustomerOrderOut,
    CustomerOrderSummary,
)

router = APIRouter(prefix="/customer-orders", tags=["Customer Orders"])


@router.post(
    "",
    response_model=CustomerOrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Customer] Buat pesanan (otomatis dipecah ke merchant order)",
)
def create_customer_order(data: CustomerOrderCreate, db: Session = Depends(get_db)):
    """Buat satu customer order. Item lintas-tenant dipecah otomatis menjadi
    beberapa merchant order. Status awal: verifying.
    """
    return customer_order_service.create_customer_order(db, data)


@router.get(
    "",
    response_model=List[CustomerOrderSummary],
    summary="[Admin] List semua customer order",
)
def list_customer_orders(
    status: Optional[CustomerOrderStatus] = Query(None, description="Filter status customer order"),
    customer_id: Optional[int] = Query(None, description="Filter order milik satu customer"),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return customer_order_service.list_customer_orders(
        db, status=status, customer_id=customer_id, offset=offset, limit=limit
    )


@router.get(
    "/{order_id}",
    response_model=CustomerOrderOut,
    summary="[Admin & Customer] Detail customer order (struk multi-tenant)",
)
def get_customer_order(order_id: int, db: Session = Depends(get_db)):
    return customer_order_service.get_customer_order_or_404(db, order_id)


@router.post(
    "/{order_id}/verify-payment",
    response_model=CustomerOrderOut,
    summary="[Customer] Tandai pembayaran terverifikasi (verifying → open)",
)
def verify_payment(order_id: int, db: Session = Depends(get_db)):
    return customer_order_service.verify_payment(db, order_id)


@router.post(
    "/{order_id}/confirm",
    response_model=CustomerOrderOut,
    summary="[Customer] Konfirmasi pesanan selesai (waiting_confirmation → done)",
)
def confirm_order(order_id: int, db: Session = Depends(get_db)):
    return customer_order_service.confirm_order(db, order_id)
