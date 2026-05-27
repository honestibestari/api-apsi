from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.review import review_service
from app.review.review_schema import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post(
    "",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Customer] Kirim ulasan & rating merchant",
)
def create_review(data: ReviewCreate, db: Session = Depends(get_db)):
    return review_service.create_review(db, data)


@router.get(
    "",
    response_model=List[ReviewOut],
    summary="[Admin/Customer] List ulasan (filter per merchant)",
)
def list_reviews(
    merchant_id: Optional[int] = Query(None, description="Filter per merchant"),
    offset:      int           = Query(0, ge=0),
    limit:       int           = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return review_service.list_reviews(db, merchant_id=merchant_id, offset=offset, limit=limit)
