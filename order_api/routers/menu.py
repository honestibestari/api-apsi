from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
import schemas

router = APIRouter(prefix="/menu", tags=["Menu"])

@router.get("/", response_model=List[schemas.MenuItemResponse], summary="Ambil semua menu")
def get_all_menu(
    kategori: Optional[schemas.CategoryEnum] = Query(None, description="Filter: makanan / minuman"),
    tersedia: Optional[bool] = Query(None, description="Filter ketersediaan"),
    db: Session = Depends(get_db)
):
    """Ambil semua menu. Bisa difilter berdasarkan kategori dan ketersediaan."""
    query = db.query(models.MenuItem)
    if kategori:
        query = query.filter(models.MenuItem.kategori == kategori)
    if tersedia is not None:
        query = query.filter(models.MenuItem.tersedia == tersedia)
    return query.order_by(models.MenuItem.kategori, models.MenuItem.nama).all()

@router.get("/makanan", response_model=List[schemas.MenuItemResponse], summary="Ambil menu makanan")
def get_menu_makanan(db: Session = Depends(get_db)):
    """Ambil semua menu makanan yang tersedia."""
    return db.query(models.MenuItem).filter(
        models.MenuItem.kategori == "makanan",
        models.MenuItem.tersedia == True
    ).all()

@router.get("/minuman", response_model=List[schemas.MenuItemResponse], summary="Ambil menu minuman")
def get_menu_minuman(db: Session = Depends(get_db)):
    """Ambil semua menu minuman yang tersedia."""
    return db.query(models.MenuItem).filter(
        models.MenuItem.kategori == "minuman",
        models.MenuItem.tersedia == True
    ).all()

@router.get("/search", response_model=List[schemas.MenuItemResponse])
def search_menu(
    nama: str = Query(..., description="Nama menu yang dicari"),
    db: Session = Depends(get_db)
):
    return db.query(models.MenuItem).filter(
        models.MenuItem.nama.ilike(f"%{nama}%")
    ).all()

@router.get("/{menu_id}", response_model=schemas.MenuItemResponse, summary="Ambil detail menu")
def get_menu_by_id(menu_id: int, db: Session = Depends(get_db)):
    """Ambil detail menu berdasarkan ID."""
    item = db.query(models.MenuItem).filter(models.MenuItem.id == menu_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Menu dengan ID {menu_id} tidak ditemukan")
    return item

@router.post("/", response_model=schemas.MenuItemResponse, summary="Tambah menu baru")
def create_menu(item: schemas.MenuItemCreate, db: Session = Depends(get_db)):
    """Tambah menu baru ke database."""
    db_item = models.MenuItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/{menu_id}", response_model=schemas.MenuItemResponse, summary="Update menu")
def update_menu(menu_id: int, item: schemas.MenuItemCreate, db: Session = Depends(get_db)):
    """Update data menu berdasarkan ID."""
    db_item = db.query(models.MenuItem).filter(models.MenuItem.id == menu_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail=f"Menu dengan ID {menu_id} tidak ditemukan")
    for key, value in item.model_dump().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{menu_id}", summary="Hapus menu")
def delete_menu(menu_id: int, db: Session = Depends(get_db)):
    """Hapus menu berdasarkan ID."""
    db_item = db.query(models.MenuItem).filter(models.MenuItem.id == menu_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail=f"Menu dengan ID {menu_id} tidak ditemukan")
    db.delete(db_item)
    db.commit()
    return {"message": f"Menu '{db_item.nama}' berhasil dihapus"}