from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_merchant
from app.merchant.merchant_model import Merchant
from app.withdrawal import withdrawal_service
from app.withdrawal.withdrawal_model import WithdrawalStatus

router = APIRouter(prefix="/tenant-balance", tags=["Tenant Balance"])


class TenantBalanceOut(BaseModel):
    """Ringkasan saldo merchant yang sedang login.

    - total_revenue : akumulasi pendapatan dari pesanan SELESAI.
    - total_balance : saldo setelah dikurangi pencairan yang sudah APPROVED
                      (= properti Merchant.balance).
    - pending       : total pencairan yang masih menunggu persetujuan (terkunci).
    - balance       : saldo yang BENAR-BENAR bisa ditarik (total_balance − pending).
    """

    balance:       float
    total_balance: float
    pending:       float
    total_revenue: float


@router.get("/me", response_model=TenantBalanceOut,
            summary="[Merchant] Saldo tersedia milik sendiri")
def my_balance(current_merchant: Merchant = Depends(get_current_merchant)):
    pending = sum(
        w.amount
        for w in current_merchant.withdrawals
        if w.status == WithdrawalStatus.PENDING
    )
    return TenantBalanceOut(
        balance       = withdrawal_service._available_balance(current_merchant),
        total_balance = current_merchant.balance,
        pending       = pending,
        total_revenue = current_merchant.total_revenue,
    )
