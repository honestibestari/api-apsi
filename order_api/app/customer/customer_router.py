from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.customer import customer_service
from app.customer.customer_schema import (
    CustomerCreate,
    CustomerOut,
    CustomerSummary,
    CustomerUpdate,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get(
    "",
    response_model=List[CustomerSummary],
    summary="List semua customer",
)
def list_customers(
    search: Optional[str] = Query(None, description="Cari nama atau email"),
    offset: int           = Query(0, ge=0),
    limit:  int           = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List customer dengan optional pencarian.

    - `?search=dika` → cari nama atau email mengandung "dika"
    - `total_orders` di response = jumlah CustomerOrder milik customer
    """
    customers = customer_service.list_customers(db, search=search, offset=offset, limit=limit)

    # Hitung total_orders dari relasi (tidak perlu query terpisah)
    result = []
    for c in customers:
        summary = CustomerSummary.model_validate(c)
        summary.total_orders = len(c.orders)
        result.append(summary)
    return result


@router.post(
    "",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Buat customer baru",
)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    """
    Buat customer baru.

    - `email` opsional tapi harus unik jika diisi
    - Customer yang sama (email sama) akan error 409
    """
    return customer_service.create_customer(db, data)


@router.get(
    "/{customer_id}",
    response_model=CustomerOut,
    summary="Detail customer",
)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Detail satu customer berdasarkan ID."""
    return customer_service.get_customer(db, customer_id)


@router.put(
    "/{customer_id}",
    response_model=CustomerOut,
    summary="Update customer (partial update)",
)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
):
    """
    Update field customer. Kirim hanya field yang ingin diubah.

    Contoh — ubah nomor HP saja:
    ```json
    { "phone": "08123456789" }
    ```
    """
    return customer_service.update_customer(db, customer_id, data)


@router.delete(
    "/{customer_id}",
    summary="Hapus customer",
)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Hapus customer secara permanen beserta semua order-nya."""
    return customer_service.delete_customer(db, customer_id)