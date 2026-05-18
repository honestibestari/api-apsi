from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
import schemas

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.get("/", response_model=List[schemas.OrderResponse], summary="Ambil semua order")
def get_all_orders(
    status: Optional[schemas.StatusEnum] = Query(None, description="Filter by status"),
    nomor_meja: Optional[int] = Query(None, description="Filter by nomor meja"),
    db: Session = Depends(get_db)
):
    """Ambil semua order. Bisa difilter berdasarkan status dan nomor meja."""
    query = db.query(models.Order)
    if status:
        query = query.filter(models.Order.status == status)
    if nomor_meja:
        query = query.filter(models.Order.nomor_meja == nomor_meja)
    return query.order_by(models.Order.created_at.desc()).all()

@router.get("/summary", summary="Ringkasan semua order")
def get_order_summary(db: Session = Depends(get_db)):
    """Ambil ringkasan statistik order."""
    from sqlalchemy import func

    total_order = db.query(models.Order).count()
    total_pendapatan = db.query(func.sum(models.Order.total_harga)).filter(
        models.Order.status == "selesai"
    ).scalar() or 0

    per_status = db.query(
        models.Order.status,
        func.count(models.Order.id).label("jumlah")
    ).group_by(models.Order.status).all()

    return {
        "total_order": total_order,
        "total_pendapatan_selesai": total_pendapatan,
        "per_status": [{"status": s, "jumlah": j} for s, j in per_status]
    }

@router.get("/aktif", response_model=List[schemas.OrderResponse], summary="Order aktif (pending & diproses)")
def get_active_orders(db: Session = Depends(get_db)):
    """Ambil order yang masih aktif (pending atau sedang diproses)."""
    return db.query(models.Order).filter(
        models.Order.status.in_(["pending", "diproses"])
    ).order_by(models.Order.created_at.asc()).all()

@router.get("/{order_id}", response_model=schemas.OrderResponse, summary="Detail order")
def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    """Ambil detail order beserta semua item berdasarkan ID."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order dengan ID {order_id} tidak ditemukan")
    return order

@router.post("/", response_model=schemas.OrderResponse, summary="Buat order baru")
def create_order(order_data: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Buat order baru dengan daftar item yang dipesan."""
    if not order_data.items:
        raise HTTPException(status_code=400, detail="Order harus memiliki minimal 1 item")

    order = models.Order(
        nama_pelanggan=order_data.nama_pelanggan,
        nomor_meja=order_data.nomor_meja,
        catatan=order_data.catatan
    )
    db.add(order)
    db.flush()

    total = 0.0
    for item_data in order_data.items:
        menu = db.query(models.MenuItem).filter(
            models.MenuItem.id == item_data.menu_item_id,
            models.MenuItem.tersedia == True
        ).first()
        if not menu:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Menu ID {item_data.menu_item_id} tidak ditemukan atau tidak tersedia"
            )
        subtotal = menu.harga * item_data.jumlah
        total += subtotal
        order_item = models.OrderItem(
            order_id=order.id,
            menu_item_id=menu.id,
            jumlah=item_data.jumlah,
            harga_satuan=menu.harga,
            subtotal=subtotal
        )
        db.add(order_item)

    order.total_harga = total
    db.commit()
    db.refresh(order)
    return order

@router.patch("/{order_id}/status", response_model=schemas.OrderResponse, summary="Update status order")
def update_order_status(order_id: int, status_data: schemas.OrderUpdateStatus, db: Session = Depends(get_db)):
    """Update status order: pending → diproses → selesai / dibatalkan."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order dengan ID {order_id} tidak ditemukan")
    order.status = status_data.status
    db.commit()
    db.refresh(order)
    return order

@router.delete("/{order_id}", summary="Hapus order")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """Hapus order beserta semua item-nya."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order dengan ID {order_id} tidak ditemukan")
    db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).delete()
    db.delete(order)
    db.commit()
    return {"message": f"Order #{order_id} atas nama '{order.nama_pelanggan}' berhasil dihapus"}