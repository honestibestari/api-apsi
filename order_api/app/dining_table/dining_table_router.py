import base64
import json
from typing import List

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.config import settings
from app.core.database import get_db
from app.dining_table import dining_table_service
from app.dining_table.dining_table_schema import (
    DiningTableCreate,
    DiningTableOut,
    DiningTableUpdate,
)

router = APIRouter(prefix="/dining-tables", tags=["Dining Tables"])


# ── CRUD admin ──────────────────────────────────────────────────────────────

@router.get("", response_model=List[DiningTableOut], summary="List semua meja (admin)")
def list_dining_tables(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return dining_table_service.list_tables(db)


@router.post("", response_model=DiningTableOut, status_code=status.HTTP_201_CREATED,
             summary="Tambah meja (admin)")
def create_dining_table(
    data: DiningTableCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return dining_table_service.create_table(db, data)


@router.patch("/{table_id}", response_model=DiningTableOut,
              summary="Update meja — rename / toggle aktif (admin)")
def update_dining_table(
    table_id: int,
    data: DiningTableUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return dining_table_service.update_table(db, table_id, data)


@router.delete("/{table_id}", summary="Hapus meja (admin)")
def delete_dining_table(
    table_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return dining_table_service.delete_table(db, table_id)


def _encode_payload(code: str, label: str) -> str:
    """Encode {code, label} jadi token URL-safe base64.

    Bukan enkripsi — siapapun bisa decode. Tujuannya cuma supaya URL
    yang dilihat user terlihat opaque dan FE cukup parse satu token
    untuk dapat kedua nilai (kode + label).
    """
    raw = json.dumps({"code": code, "label": label}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@router.get(
    "/scan",
    summary="Scan QR → redirect ke frontend dengan token berisi code+label",
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
      3. Encode {code, label} jadi token base64 URL-safe.
      4. Redirect 302 ke `<FRONTEND_URL>/?t=<token>`.
      5. FE decode token (atob + JSON.parse) → langsung dapat code & label
         tanpa hit API kedua.
    """
    table = dining_table_service.get_by_code_or_404(db, code)
    token = _encode_payload(table.code, table.label)
    target = f"{settings.frontend_url.rstrip('/')}/?t={token}"
    return RedirectResponse(url=target, status_code=302)
