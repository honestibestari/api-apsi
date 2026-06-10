"""Logika bisnis untuk DiningTable."""
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dining_table.dining_table_model import DiningTable
from app.dining_table.dining_table_schema import DiningTableCreate, DiningTableUpdate


def list_tables(db: Session) -> List[DiningTable]:
    return db.query(DiningTable).order_by(DiningTable.label).all()


def get_or_404(db: Session, table_id: int) -> DiningTable:
    table = db.query(DiningTable).filter(DiningTable.id == table_id).first()
    if not table:
        raise HTTPException(404, "Meja tidak ditemukan")
    return table


def create_table(db: Session, data: DiningTableCreate) -> DiningTable:
    bentrok = db.query(DiningTable).filter(DiningTable.label == data.label).first()
    if bentrok:
        raise HTTPException(409, f"Meja dengan label '{data.label}' sudah ada")
    table = DiningTable(label=data.label, is_active=data.is_active)
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


def update_table(db: Session, table_id: int, data: DiningTableUpdate) -> DiningTable:
    table = get_or_404(db, table_id)
    if data.label is not None:
        label = data.label.strip()
        if not label:
            raise HTTPException(422, "Label meja tidak boleh kosong")
        bentrok = db.query(DiningTable).filter(
            DiningTable.label == label,
            DiningTable.id != table_id,
        ).first()
        if bentrok:
            raise HTTPException(409, f"Meja dengan label '{label}' sudah ada")
        table.label = label
    if data.is_active is not None:
        table.is_active = data.is_active
    db.commit()
    db.refresh(table)
    return table


def delete_table(db: Session, table_id: int) -> dict:
    table = get_or_404(db, table_id)
    label = table.label
    db.delete(table)
    db.commit()
    return {"message": f"Meja '{label}' berhasil dihapus", "id": table_id}


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
