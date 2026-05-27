from typing import List, Optional

from sqlalchemy.orm import Session

from app.merchant.merchant_service import get_merchant_or_404
from app.review.review_model import Review
from app.review.review_schema import ReviewCreate


def list_reviews(
    db: Session,
    merchant_id: Optional[int] = None,
    offset: int = 0,
    limit: int = 50,
) -> List[Review]:
    query = db.query(Review).order_by(Review.created_at.desc())
    if merchant_id is not None:
        query = query.filter(Review.merchant_id == merchant_id)
    return query.offset(offset).limit(limit).all()


def create_review(db: Session, data: ReviewCreate) -> Review:
    get_merchant_or_404(db, data.merchant_id)  # 404 bila merchant tidak ada
    review = Review(
        merchant_id=data.merchant_id,
        customer_order_id=data.customer_order_id,
        rating=data.rating,
        komentar=data.komentar,
        pelanggan=data.pelanggan,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
