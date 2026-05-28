from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.customer.customer_model import Customer
from app.customer.customer_schema import CustomerCreate, CustomerUpdate


# ── Helper ────────────────────────────────────────────────────────────────────

def _cek_duplikat_email(db: Session, email: str, exclude_id: Optional[int] = None) -> None:
    """Raise 409 jika email sudah dipakai customer lain."""
    query = db.query(Customer).filter(Customer.email == email)
    if exclude_id:
        query = query.filter(Customer.id != exclude_id)
    if query.first():
        raise HTTPException(409, f"Email '{email}' sudah terdaftar")


def get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, f"Customer ID {customer_id} tidak ditemukan")
    return customer


# ── CRUD ──────────────────────────────────────────────────────────────────────

def list_customers(
    db: Session,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> List[Customer]:
    """List customer dengan optional pencarian nama / email."""
    limit = min(limit, 100)
    query = db.query(Customer).order_by(Customer.created_at.desc())

    if search:
        like = f"%{search}%"
        query = query.filter(
            Customer.nama.ilike(like) | Customer.email.ilike(like)
        )

    return query.offset(offset).limit(limit).all()


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    """Buat customer baru.

    Jika email diisi, harus unik — raise 409 jika sudah ada.
    """
    if data.email:
        _cek_duplikat_email(db, data.email)

    customer = Customer(
        nama  = data.nama,
        email = data.email,
        phone = data.phone,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int) -> Customer:
    return get_customer_or_404(db, customer_id)


def update_customer(db: Session, customer_id: int, data: CustomerUpdate) -> Customer:
    """Partial update — hanya field yang dikirim yang berubah."""
    customer = get_customer_or_404(db, customer_id)

    if data.email and data.email != customer.email:
        _cek_duplikat_email(db, data.email, exclude_id=customer_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int) -> dict:
    """Hapus customer.

    Catatan: CustomerOrder yang sudah ada akan ikut terhapus
    jika relasi dikonfigurasi cascade, atau error jika tidak.
    Pastikan cascade='all, delete-orphan' di relasi Customer.orders.
    """
    customer = get_customer_or_404(db, customer_id)
    nama = customer.nama

    db.delete(customer)
    db.commit()
    return {"message": f"Customer '{nama}' berhasil dihapus", "id": customer_id}