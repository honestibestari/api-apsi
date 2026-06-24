from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.platform_setting import platform_setting_service as svc
from app.platform_setting.platform_setting_schema import (
    PlatformFeePublic,
    PlatformSettingOut,
    PlatformSettingUpdate,
)

router = APIRouter(prefix="/platform-settings", tags=["Platform Settings"])


@router.get("/public", response_model=PlatformFeePublic,
            summary="[Publik] Parameter biaya layanan untuk estimasi di cart")
def public_fee(db: Session = Depends(get_db)):
    """Dipakai FE customer untuk menampilkan estimasi biaya layanan sebelum order.

    Perhitungan final tetap dilakukan server saat order dibuat — ini hanya
    pratinjau agar angka di cart konsisten.
    """
    s = svc.get_settings(db)
    return PlatformFeePublic(fee_rate=s.fee_rate, fee_fixed=s.fee_fixed, is_active=s.is_active)


@router.get("", response_model=PlatformSettingOut,
            summary="[Admin] Lihat pengaturan biaya layanan platform")
def get_platform_settings(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    return svc.get_settings(db)


@router.put("", response_model=PlatformSettingOut,
            summary="[Admin] Ubah besar biaya layanan platform")
def update_platform_settings(
    data: PlatformSettingUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    return svc.update_settings(db, data)
