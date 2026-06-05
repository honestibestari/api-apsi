from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.review.review_model import Review
from app.review.review_schema import ReviewCreate


def list_reviews(
    db: Session,
    merchant_id: Optional[int] = None,
    offset: int = 0,
    limit: int = 20,
) -> List[Review]:
    query = db.query(Review).order_by(Review.created_at.desc())
    if merchant_id:
        query = query.filter(Review.merchant_id == merchant_id)
    return query.offset(offset).limit(limit).all()


def create_review(db: Session, data: ReviewCreate) -> Review:
    review = Review(
        merchant_id = data.merchant_id,
        customer_id = data.customer_id,
        pelanggan   = data.pelanggan,
        rating      = data.rating,
        komentar    = data.komentar,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review_id: int) -> dict:
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(404, "Review tidak ditemukan")
    db.delete(review)
    db.commit()
    return {"message": "Review berhasil dihapus", "id": review_id}