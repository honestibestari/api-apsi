from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.customer.customer_model import Customer
from app.customer.customer_schema import CustomerCreate, CustomerUpdate


def _cek_duplikat(db: Session, email: Optional[str], phone: Optional[str],
                  exclude_id: Optional[int] = None) -> None:
    if email:
        q = db.query(Customer).filter(Customer.email == email)
        if exclude_id:
            q = q.filter(Customer.id != exclude_id)
        if q.first():
            raise HTTPException(409, f"Email '{email}' sudah terdaftar")
    if phone:
        q = db.query(Customer).filter(Customer.phone == phone)
        if exclude_id:
            q = q.filter(Customer.id != exclude_id)
        if q.first():
            raise HTTPException(409, f"Nomor HP '{phone}' sudah terdaftar")


def get_customer_or_404(db: Session, customer_id: int) -> Customer:
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, f"Customer ID {customer_id} tidak ditemukan")
    return c


def list_customers(
    db: Session,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> List[Customer]:
    limit = min(limit, 100)
    query = db.query(Customer).order_by(Customer.created_at.desc())
    if search:
        like = f"%{search}%"
        query = query.filter(
            Customer.nama.ilike(like) |
            Customer.email.ilike(like) |
            Customer.phone.ilike(like)
        )
    return query.offset(offset).limit(limit).all()


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    _cek_duplikat(db, data.email, data.phone)
    customer = Customer(
        nama  = data.nama,
        email = data.email,
        phone = data.phone,
        no_wa = data.no_wa,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(db: Session, customer_id: int, data: CustomerUpdate) -> Customer:
    customer = get_customer_or_404(db, customer_id)
    if data.email or data.phone:
        _cek_duplikat(db, data.email, data.phone, exclude_id=customer_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int) -> dict:
    customer = get_customer_or_404(db, customer_id)
    nama = customer.nama
    db.delete(customer)
    db.commit()
    return {"message": f"Customer '{nama}' berhasil dihapus", "id": customer_id}