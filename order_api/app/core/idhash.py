"""ID ter-hash (opaque & tamper-proof) untuk endpoint publik.

Mengubah id integer berurutan menjadi token acak-tampak yang tidak bisa
di-enumerate / ditebak, dan tidak bisa dipalsukan tanpa SECRET_KEY. Reversible:
server men-decode kembali ke id untuk lookup.

Token = base64url("<salt>:<id>") + "." + HMAC-SHA256(secret, "<salt>:<id>")[:20]

`salt` mengikat token ke jenis entitas tertentu (mis. "customer_order"), sehingga
token satu entitas tidak bisa dipakai di endpoint entitas lain.
"""
import base64
import hashlib
import hmac
from typing import Optional

from app.core.config import settings


def _sig(payload: str) -> str:
    mac = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).rstrip(b"=").decode()[:20]


def encode(salt: str, value: int) -> str:
    raw = f"{salt}:{value}"
    body = base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()
    return f"{body}.{_sig(raw)}"


def decode(salt: str, token: str) -> Optional[int]:
    """Kembalikan id bila token valid & cocok salt; None bila tidak valid/dipalsukan."""
    try:
        body, sig = token.rsplit(".", 1)
        pad = "=" * (-len(body) % 4)
        raw = base64.urlsafe_b64decode(body + pad).decode()
        salt_in, value = raw.split(":", 1)
        if salt_in != salt:
            return None
        if not hmac.compare_digest(sig, _sig(raw)):
            return None
        return int(value)
    except Exception:  # noqa: BLE001 — token rusak/format salah → anggap tidak valid
        return None
