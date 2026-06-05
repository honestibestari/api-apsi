from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.customer import customer_service
from app.customer.customer_schema import CustomerCreate, CustomerOut, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=List[CustomerOut], summary="[Admin] List semua customer")
def list_customers(
    search:  Optional[str] = Query(None, description="Cari nama/email/phone"),
    offset:  int = Query(0, ge=0),
    limit:   int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return customer_service.list_customers(db, search=search, offset=offset, limit=limit)


@router.get("/{customer_id}", response_model=CustomerOut, summary="[Admin] Detail customer")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return customer_service.get_customer_or_404(db, customer_id)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED,
             summary="[Admin] Buat customer baru")
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return customer_service.create_customer(db, data)


@router.put("/{customer_id}", response_model=CustomerOut, summary="[Admin] Update customer")
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return customer_service.update_customer(db, customer_id, data)


@router.delete("/{customer_id}", summary="[Admin] Hapus customer")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return customer_service.delete_customer(db, customer_id)