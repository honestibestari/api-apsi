from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dining_table import dining_table_service

router = APIRouter(prefix="/dining-tables", tags=["Dining Tables"])


@router.get(
    "/scan",
    summary="Scan QR → redirect ke frontend order page",
    response_class=RedirectResponse,
    status_code=302,
)
def scan_dining_table(
    code: str = Query(..., description="Kode unik dining table yang di-encode di QR"),
    db: Session = Depends(get_db),
):
    """Endpoint utama yang dituju oleh QR code.

    Alur:
      1. HP scan QR → buka `GET /dining-tables/scan?code=<kode>`
      2. Backend validasi: dining table ada & aktif (404 jika tidak).
      3. Redirect 302 ke `<FRONTEND_URL>/?table=<kode>` — browser HP
         otomatis lompat, frontend tinggal baca query param.
    """
    table = dining_table_service.get_by_code_or_404(db, code)
    target = f"{settings.frontend_url.rstrip('/')}/?table={table.code}"
    return RedirectResponse(url=target, status_code=302)
