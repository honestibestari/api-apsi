from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.maintenance import maintenance_service

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


@router.api_route(
    "/sweep",
    methods=["POST", "GET"],
    summary="Jalankan sweep timeout order (manual / cron eksternal)",
)
def sweep(db: Session = Depends(get_db)):
    """Picu sweep maintenance sekali jalan. Berguna saat scheduler internal
    dimatikan (mis. lingkungan serverless) — panggil endpoint ini lewat cron.
    GET didukung karena Vercel Cron & layanan cron gratis umumnya hanya GET.
    Return ringkasan jumlah order yang terpengaruh per tahap.
    """
    return maintenance_service.run_maintenance_sweep(db)
