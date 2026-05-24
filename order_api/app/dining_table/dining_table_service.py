"""Logika bisnis untuk DiningTable."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dining_table.dining_table_model import DiningTable


def get_by_code_or_404(db: Session, code: str) -> DiningTable:
    """Ambil dining table aktif berdasarkan kode QR, atau 404."""
    table = (
        db.query(DiningTable)
        .filter(
            DiningTable.code == code,
            DiningTable.is_active.is_(True),
        )
        .first()
    )
    if not table:
        raise HTTPException(
            status_code=404,
            detail=f"Dining table dengan kode '{code}' tidak ditemukan atau tidak aktif",
        )
    return table
