from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.attachment import attachment_service
from app.banner.banner_model import Banner
from app.banner.banner_schema import BannerCreate, BannerOut, BannerUpdate
from app.core.auth import require_admin
from app.core.database import get_db

router = APIRouter(prefix="/banners", tags=["Banners"])


@router.post("/upload-image", summary="Upload gambar banner (admin) → kembalikan URL")
async def upload_banner_image(
    file: UploadFile = File(...),
    _=Depends(require_admin),
):
    """Unggah gambar banner; kembalikan { url } untuk disimpan di image_url banner.

    Terpisah dari create/update agar bisa dipakai sebelum banner punya id.
    """
    url = await attachment_service.store_image(file, "banners")
    return {"url": url}


@router.get("", response_model=List[BannerOut], summary="List banner aktif (publik)")
def list_active_banners(db: Session = Depends(get_db)):
    """Untuk home customer — hanya banner aktif, terurut sort_order."""
    return (
        db.query(Banner)
        .filter(Banner.is_active.is_(True))
        .order_by(Banner.sort_order, Banner.id)
        .all()
    )


@router.get("/all", response_model=List[BannerOut], summary="List semua banner (admin)")
def list_all_banners(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return db.query(Banner).order_by(Banner.sort_order, Banner.id).all()


@router.post("", response_model=BannerOut, status_code=status.HTTP_201_CREATED,
             summary="Tambah banner (admin)")
def create_banner(
    data: BannerCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    banner = Banner(**data.model_dump())
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


@router.patch("/{banner_id}", response_model=BannerOut, summary="Update banner (admin)")
def update_banner(
    banner_id: int,
    data: BannerUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(404, "Banner tidak ditemukan")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(banner, field, value)
    db.commit()
    db.refresh(banner)
    return banner


@router.delete("/{banner_id}", summary="Hapus banner (admin)")
def delete_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(404, "Banner tidak ditemukan")
    title = banner.title
    db.delete(banner)
    db.commit()
    return {"message": f"Banner '{title}' berhasil dihapus", "id": banner_id}
