"""Logika biaya layanan platform (pendapatan platform).

Sumber kebenaran tunggal untuk perhitungan biaya layanan dipakai oleh:
  • customer_order_service  → saat order dibuat & saat total dihitung ulang,
  • maintenance_service     → saat refund proporsional dibentuk,
  • platform_setting_router → endpoint admin & publik.

Semua nominal dibulatkan ke rupiah bulat (round) agar `fee + net = gross`
selalu pas — sistem masih memakai Float untuk uang.
"""
from sqlalchemy.orm import Session

from app.platform_setting.platform_setting_model import PlatformSetting
from app.platform_setting.platform_setting_schema import PlatformSettingUpdate


def get_settings(db: Session) -> PlatformSetting:
    """Ambil baris singleton; buat dengan default bila belum ada."""
    setting = db.query(PlatformSetting).order_by(PlatformSetting.id.asc()).first()
    if not setting:
        setting = PlatformSetting(fee_rate=0.0, fee_fixed=0.0, is_active=True)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def update_settings(db: Session, data: PlatformSettingUpdate) -> PlatformSetting:
    setting = get_settings(db)
    if data.fee_rate is not None:
        setting.fee_rate = data.fee_rate
    if data.fee_fixed is not None:
        setting.fee_fixed = data.fee_fixed
    if data.is_active is not None:
        setting.is_active = data.is_active
    db.commit()
    db.refresh(setting)
    return setting


def compute_fee(subtotal: float, setting: PlatformSetting) -> float:
    """Biaya layanan = round(rate% × subtotal + fixed). 0 bila fitur nonaktif."""
    if not setting or not setting.is_active:
        return 0.0
    fee = (subtotal or 0.0) * (setting.fee_rate / 100.0) + setting.fee_fixed
    return float(round(max(fee, 0.0)))


def fee_portion(total_fee: float, part_amount: float, whole_amount: float) -> float:
    """Porsi biaya layanan untuk sebagian nilai order (proporsional terhadap nilai).

    Dipakai saat refund parsial: porsi fee yang dikembalikan = total_fee ×
    (nilai_tenant_batal / nilai_seluruh_tenant). Dibulatkan ke rupiah bulat.
    """
    if not total_fee or whole_amount <= 0:
        return 0.0
    return float(round(total_fee * (part_amount / whole_amount)))
