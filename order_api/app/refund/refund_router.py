from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.refund import refund_service
from app.refund.refund_model import StatusRefund
from app.refund.refund_schema import RefundCreate, RefundOut

router = APIRouter(prefix="/refunds", tags=["Refunds"])


@router.get("", response_model=List[RefundOut], summary="List refund (admin)")
def list_refunds(
    id_pesanan: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return refund_service.list_refunds(db, id_pesanan=id_pesanan)


@router.get("/{refund_id}", response_model=RefundOut, summary="Detail refund")
def get_refund(refund_id: int, db: Session = Depends(get_db)):
    return refund_service.get_refund_or_404(db, refund_id)


@router.post("", response_model=RefundOut, status_code=status.HTTP_201_CREATED,
             summary="Ajukan refund (customer)")
def create_refund(data: RefundCreate, db: Session = Depends(get_db)):
    return refund_service.create_refund(db, data)


@router.put("/{refund_id}/status", response_model=RefundOut,
            summary="Setujui atau tolak refund (admin)")
def update_refund_status(
    refund_id: int,
    status: StatusRefund = Query(..., description="disetujui | ditolak"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return refund_service.update_refund_status(db, refund_id, status)