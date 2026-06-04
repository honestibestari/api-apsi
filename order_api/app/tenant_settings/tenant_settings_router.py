from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_merchant
from app.core.database import get_db
from app.merchant.merchant_model import Merchant
from app.tenant_settings.tenant_model_settings import TenantSettings
from app.tenant_settings.tenant_settings_schema import TenantSettingsOut, TenantSettingsUpdate

router = APIRouter(prefix="/tenant-settings", tags=["Tenant Settings"])


def _get_or_create(db: Session, merchant_id: int) -> TenantSettings:
    settings = db.query(TenantSettings).filter(
        TenantSettings.id_tenant == merchant_id
    ).first()
    if not settings:
        settings = TenantSettings(id_tenant=merchant_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/me", response_model=TenantSettingsOut,
            summary="[Merchant] Lihat pengaturan sendiri")
def get_my_settings(
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return _get_or_create(db, current_merchant.id)


@router.put("/me", response_model=TenantSettingsOut,
            summary="[Merchant] Update pengaturan")
def update_my_settings(
    data: TenantSettingsUpdate,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    settings = _get_or_create(db, current_merchant.id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings