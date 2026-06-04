from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.user_notification.notification_user_model import NotificationUser
from app.user_notification.notification_user_schema import (
    NotificationUserMarkRead,
    NotificationUserOut,
)

router = APIRouter(prefix="/user-notifications", tags=["User Notifications"])


@router.get("/{customer_id}", response_model=List[NotificationUserOut],
            summary="List notifikasi customer")
def list_notifications(
    customer_id: int,
    only_unread: bool = Query(False, description="true = belum dibaca saja"),
    offset: int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(NotificationUser)
        .filter(NotificationUser.id_user == customer_id)
        .order_by(NotificationUser.timestamp.desc())
    )
    if only_unread:
        query = query.filter(NotificationUser.is_read.is_(False))
    return query.offset(offset).limit(limit).all()


@router.post("/{customer_id}/read", summary="Tandai beberapa notifikasi dibaca")
def mark_read(
    customer_id: int,
    data: NotificationUserMarkRead,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(NotificationUser)
        .filter(
            NotificationUser.id_user == customer_id,
            NotificationUser.id.in_(data.ids),
        )
        .all()
    )
    for n in rows:
        n.is_read = True
    db.commit()
    return {"message": f"{len(rows)} notifikasi ditandai sudah dibaca"}


@router.post("/{customer_id}/read-all", summary="Tandai semua notifikasi dibaca")
def mark_all_read(customer_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(NotificationUser)
        .filter(
            NotificationUser.id_user == customer_id,
            NotificationUser.is_read.is_(False),
        )
        .all()
    )
    for n in rows:
        n.is_read = True
    db.commit()
    return {"message": f"{len(rows)} notifikasi ditandai sudah dibaca"}