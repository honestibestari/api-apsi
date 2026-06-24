from typing import List, Optional
from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_merchant, require_admin
from app.core.database import get_db
from app.merchant.merchant_model import Merchant
from app.withdrawal import withdrawal_service
from app.withdrawal.withdrawal_model import WithdrawalStatus
from app.withdrawal.withdrawal_schema import (
    BankAccountCreate,
    BankAccountOut,
    WithdrawalCreate,
    WithdrawalOut,
    WithdrawalReject,
    WithdrawalSummary,
)

router = APIRouter(prefix="/withdrawals", tags=["Withdrawals"])


@router.get("/summary", response_model=WithdrawalSummary, summary="[Admin] Ringkasan statistik withdrawal")
def withdrawal_summary(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return withdrawal_service.get_summary(db)


@router.get("", response_model=List[WithdrawalOut], summary="[Admin] List semua withdrawal")
def list_withdrawals(
    merchant_id: Optional[int]              = Query(None),
    status:      Optional[WithdrawalStatus] = Query(None),
    offset:      int = Query(0, ge=0),
    limit:       int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return withdrawal_service.list_withdrawals(
        db, merchant_id=merchant_id, status=status, offset=offset, limit=limit
    )


@router.get("/me", response_model=List[WithdrawalOut],
            summary="[Merchant] List withdrawal milik sendiri")
def list_my_withdrawals(
    status: Optional[WithdrawalStatus] = Query(None),
    offset: int = Query(0, ge=0),
    limit:  int = Query(20, ge=1, le=100),
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return withdrawal_service.list_withdrawals(
        db, merchant_id=current_merchant.id, status=status, offset=offset, limit=limit
    )


# ── Rekening bank tersimpan (milik merchant) ─────────────────────────────────
# Didefinisikan sebelum route withdrawal lain yang generik agar path "bank-accounts"
# tidak rancu. Semua dibatasi ke merchant pemilik token.

@router.get("/bank-accounts", response_model=List[BankAccountOut],
            summary="[Merchant] List rekening tersimpan milik sendiri")
def list_bank_accounts(
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return withdrawal_service.list_bank_accounts(db, current_merchant.id)


@router.post("/bank-accounts", response_model=BankAccountOut,
             status_code=status.HTTP_201_CREATED,
             summary="[Merchant] Tambah rekening tujuan pencairan")
def create_bank_account(
    data: BankAccountCreate,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return withdrawal_service.create_bank_account(db, current_merchant.id, data)


@router.delete("/bank-accounts/{account_id}",
               summary="[Merchant] Hapus rekening tersimpan milik sendiri")
def delete_bank_account(
    account_id: int,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return withdrawal_service.delete_bank_account(db, current_merchant.id, account_id)


@router.post("", response_model=WithdrawalOut, status_code=status.HTTP_201_CREATED,
             summary="[Merchant] Ajukan penarikan dana")
def create_withdrawal(
    data: WithdrawalCreate,
    current_merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return withdrawal_service.create_withdrawal(db, current_merchant.id, data)


@router.put("/{withdrawal_id}/approve", response_model=WithdrawalOut,
            summary="[Admin] Setujui withdrawal")
def approve_withdrawal(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return withdrawal_service.approve_withdrawal(
        db, withdrawal_id, processed_by=current_admin.id
    )


@router.put("/{withdrawal_id}/reject", response_model=WithdrawalOut,
            summary="[Admin] Tolak withdrawal")
def reject_withdrawal(
    withdrawal_id: int,
    payload: Optional[WithdrawalReject] = Body(None),
    note: Optional[str] = Query(None, description="Alasan penolakan (fallback)"),
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    # Terima alasan dari body JSON (utama) maupun query param (kompatibilitas lama).
    final_note = (payload.note if payload else None) or note
    return withdrawal_service.reject_withdrawal(
        db, withdrawal_id, note=final_note, processed_by=current_admin.id
    )
