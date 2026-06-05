from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.review import review_service
from app.review.review_schema import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("", response_model=List[ReviewOut], summary="List review")
def list_reviews(
    merchant_id: Optional[int] = Query(None, description="Filter per merchant"),
    offset:      int = Query(0, ge=0),
    limit:       int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Bisa diakses siapa saja — customer perlu lihat ulasan merchant."""
    return review_service.list_reviews(db, merchant_id=merchant_id, offset=offset, limit=limit)


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED,
             summary="Buat review")
def create_review(data: ReviewCreate, db: Session = Depends(get_db)):
    """Customer buat review — tidak perlu login."""
    return review_service.create_review(db, data)


@router.delete("/{review_id}", summary="[Admin] Hapus review")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return review_service.delete_review(db, review_id)