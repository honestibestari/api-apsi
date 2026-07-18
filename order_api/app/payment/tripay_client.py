"""Klien HTTP untuk payment gateway Tripay.

Dokumentasi: https://tripay.co.id/developer
Semua kredensial dibaca dari settings (.env backend) — tidak ada yang di-hardcode
dan tidak ada yang bocor ke frontend.

Konvensi Tripay:
  • Auth API      : header `Authorization: Bearer <api_key>`.
  • Signature buat transaksi : HMAC-SHA256(private_key, merchant_code + merchant_ref + amount).
  • Signature callback       : HMAC-SHA256(private_key, raw_json_body) di header
                               `X-Callback-Signature`.
  • Nominal = integer rupiah (tanpa desimal).
"""
import hashlib
import hmac
import re
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from app.core.config import settings

_TIMEOUT = 20.0  # detik


def base_url() -> str:
    if (settings.tripay_mode or "").lower() == "production":
        return "https://tripay.co.id/api"
    return "https://tripay.co.id/api-sandbox"


def is_configured() -> bool:
    return bool(
        settings.tripay_api_key
        and settings.tripay_private_key
        and settings.tripay_merchant_code
    )


def _request(method: str, path: str, *, params: Optional[dict] = None,
             json: Optional[dict] = None) -> Any:
    """Kirim request ke Tripay & kembalikan field `data` dari respons.

    Melempar HTTPException 502 bila Tripay tidak bisa dihubungi / menolak —
    pemanggil yang butuh silent-fail (mis. rekonsiliasi polling) harus meng-catch.
    """
    headers = {"Authorization": f"Bearer {settings.tripay_api_key}"}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            res = client.request(method, base_url() + path,
                                 headers=headers, params=params, json=json)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Gagal menghubungi Tripay: {exc}")

    try:
        body = res.json()
    except ValueError:
        raise HTTPException(502, f"Respons Tripay tidak valid (HTTP {res.status_code})")

    if res.status_code >= 400 or not body.get("success", False):
        pesan = body.get("message") or f"HTTP {res.status_code}"
        raise HTTPException(502, f"Tripay menolak permintaan: {pesan}")
    return body.get("data")


def _signature(merchant_ref: str, amount: int) -> str:
    payload = f"{settings.tripay_merchant_code}{merchant_ref}{amount}"
    return hmac.new(
        settings.tripay_private_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_transaction(
    *,
    method: str,
    merchant_ref: str,
    amount: int,
    customer_name: str,
    customer_email: str,
    customer_phone: Optional[str],
    order_items: list[dict],
    expired_time: Optional[int] = None,
    callback_url: Optional[str] = None,
    return_url: Optional[str] = None,
) -> dict:
    """Buat closed transaction di Tripay. `amount` integer rupiah.

    Respons penting: reference, checkout_url, pay_code (VA), qr_string (QRIS),
    fee_customer, expired_time (unix), instructions[{title, steps[]}], status.
    """
    payload: dict[str, Any] = {
        "method":         method,
        "merchant_ref":   merchant_ref,
        "amount":         amount,
        "customer_name":  customer_name,
        "customer_email": customer_email,
        "order_items":    order_items,
        "signature":      _signature(merchant_ref, amount),
    }
    if customer_phone:
        payload["customer_phone"] = customer_phone
    if expired_time:
        payload["expired_time"] = expired_time
    if callback_url:
        payload["callback_url"] = callback_url
    if return_url:
        payload["return_url"] = return_url
    return _request("POST", "/transaction/create", json=payload)


def get_transaction(reference: str) -> dict:
    """Detail transaksi by reference Tripay — dipakai rekonsiliasi bila webhook gagal."""
    return _request("GET", "/transaction/detail", params={"reference": reference})


def get_payment_channels() -> list[dict]:
    """Daftar channel pembayaran merchant + struktur fee per channel."""
    return _request("GET", "/merchant/payment-channel") or []


def calculate_fee(code: str, amount: int) -> list[dict]:
    """Kalkulasi fee sebuah channel untuk nominal tertentu."""
    return _request("GET", "/merchant/fee-calculator",
                    params={"code": code, "amount": amount}) or []


def verify_callback_signature(raw_body: bytes, signature: str) -> bool:
    """Verifikasi header X-Callback-Signature = HMAC-SHA256(private_key, raw body)."""
    if not signature or not settings.tripay_private_key:
        return False
    expected = hmac.new(
        settings.tripay_private_key.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


_TAG_RE = re.compile(r"<[^>]+>")


def flatten_instructions(instructions: Any) -> list[str]:
    """Ratakan instructions Tripay [{title, steps[]}] → list kalimat polos.

    Steps dari Tripay mengandung tag HTML (mis. <b>...</b>) — dibuang agar aman
    dirender sebagai teks di frontend.
    """
    result: list[str] = []
    for block in instructions or []:
        for step in block.get("steps") or []:
            text = _TAG_RE.sub("", str(step)).strip()
            if text:
                result.append(text)
    return result
