"""Pengiriman email notifikasi pesanan (SMTP).

Kredensial dari settings (ADMIN_EMAIL / ADMIN_EMAIL_PASSWORD). Untuk Gmail,
gunakan App Password. Pengiriman dilewati diam-diam bila kredensial kosong,
agar pembuatan order tidak pernah gagal hanya karena email.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

BRAND = "#1D3A27"
BRAND_LIGHT = "#2d5a3d"
GOLD = "#C8961A"


def _rupiah(n) -> str:
    try:
        return "Rp" + f"{int(round(float(n))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp0"


def _tenant_rows(order) -> str:
    """Bangun blok HTML daftar item per tenant."""
    blocks = []
    for mo in (order.merchant_orders or []):
        items = "".join(
            f"""
            <tr>
              <td style="padding:2px 0;color:#374151;font-size:13px;">
                {it.jumlah}× {(it.product.nama if it.product else 'Produk')}
              </td>
              <td align="right" style="padding:2px 0;color:#6b7280;font-size:13px;white-space:nowrap;">
                {_rupiah(it.subtotal)}
              </td>
            </tr>"""
            for it in (mo.items or [])
        )
        blocks.append(f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="border:1px solid #eef0f2;border-radius:12px;margin:0 0 12px;background:#ffffff;">
          <tr>
            <td style="padding:12px 14px;border-bottom:1px solid #f3f4f6;">
              <span style="font-weight:700;color:{BRAND};font-size:14px;">
                {mo.merchant_nama or ('Tenant #' + str(mo.merchant_id))}
              </span>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 14px 4px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{items}</table>
            </td>
          </tr>
          <tr>
            <td style="padding:6px 14px 12px;border-top:1px solid #f3f4f6;">
              <table role="presentation" width="100%"><tr>
                <td style="font-size:12px;color:#9ca3af;">Subtotal tenant</td>
                <td align="right" style="font-size:13px;font-weight:700;color:{BRAND};">{_rupiah(mo.total_harga)}</td>
              </tr></table>
            </td>
          </tr>
        </table>""")
    return "".join(blocks)


def build_order_created_html(order, view_url: str) -> str:
    """Email HTML untuk konfirmasi pesanan dibuat, dengan tombol buka kembali order."""
    nama = (order.customer.nama if order.customer else None) or "Pelanggan"
    meja = order.no_meja or "-"
    metode = order.metode_pembayaran or "-"
    return f"""\
<!DOCTYPE html>
<html lang="id">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f5f7;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,0.06);">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,{BRAND_LIGHT} 0%,{BRAND} 100%);padding:28px 24px;">
          <p style="margin:0;color:#ffffff;font-size:20px;font-weight:800;letter-spacing:.3px;">Teras LA DineHub</p>
          <p style="margin:6px 0 0;color:#d9e4dd;font-size:13px;">Pesananmu sudah kami terima ✓</p>
        </td></tr>

        <!-- Greeting -->
        <tr><td style="padding:24px 24px 8px;">
          <p style="margin:0 0 4px;font-size:15px;color:#111827;">Halo <b>{nama}</b>,</p>
          <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.6;">
            Terima kasih! Pesananmu dengan nomor
            <b style="color:{BRAND};">{order.order_code}</b> berhasil dibuat.
            Lanjutkan pembayaran &amp; pantau statusnya lewat tombol di bawah.
          </p>
        </td></tr>

        <!-- Info ringkas -->
        <tr><td style="padding:12px 24px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:#f9fafb;border:1px solid #eef0f2;border-radius:12px;">
            <tr>
              <td style="padding:12px 14px;font-size:12px;color:#9ca3af;">No. Meja</td>
              <td align="right" style="padding:12px 14px;font-size:13px;font-weight:600;color:#1f2937;">{meja}</td>
            </tr>
            <tr>
              <td style="padding:0 14px 12px;font-size:12px;color:#9ca3af;">Metode Pembayaran</td>
              <td align="right" style="padding:0 14px 12px;font-size:13px;font-weight:600;color:#1f2937;">{metode}</td>
            </tr>
            <tr>
              <td style="padding:10px 14px;font-size:13px;font-weight:700;color:#111827;border-top:1px solid #eef0f2;">Total</td>
              <td align="right" style="padding:10px 14px;font-size:15px;font-weight:800;color:{BRAND};border-top:1px solid #eef0f2;">{_rupiah(order.total_harga)}</td>
            </tr>
          </table>
        </td></tr>

        <!-- Per tenant -->
        <tr><td style="padding:6px 24px 0;">
          <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.4px;">
            Rincian Pesanan
          </p>
          {_tenant_rows(order)}
        </td></tr>

        <!-- CTA -->
        <tr><td align="center" style="padding:10px 24px 28px;">
          <a href="{view_url}" target="_blank"
             style="display:inline-block;background:linear-gradient(135deg,{BRAND_LIGHT} 0%,{BRAND} 100%);
                    color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;
                    padding:14px 28px;border-radius:14px;box-shadow:0 6px 16px rgba(29,58,39,.32);">
            Buka Pesanan Saya
          </a>
          <p style="margin:14px 0 0;font-size:11px;color:#9ca3af;line-height:1.5;">
            Tombol tidak berfungsi? Salin tautan ini ke browser:<br>
            <span style="color:{GOLD};word-break:break-all;">{view_url}</span>
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:18px 24px;border-top:1px solid #eef0f2;">
          <p style="margin:0;font-size:11px;color:#9ca3af;line-height:1.6;">
            Email ini dikirim otomatis oleh Teras LA DineHub. Mohon jangan balas email ini.
          </p>
        </td></tr>

      </table>
      <p style="margin:14px 0 0;font-size:11px;color:#b0b6bd;">© Teras LA DineHub</p>
    </td></tr>
  </table>
</body>
</html>"""


def build_refund_email_html(order, nominal, refund_url: str) -> str:
    """Email pemberitahuan refund + tombol untuk memilih metode (e-wallet)."""
    nama = (order.customer.nama if order.customer else None) or "Pelanggan"
    return f"""\
<!DOCTYPE html>
<html lang="id">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f5f7;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,0.06);">

        <tr><td style="background:linear-gradient(135deg,{BRAND_LIGHT} 0%,{BRAND} 100%);padding:28px 24px;">
          <p style="margin:0;color:#ffffff;font-size:20px;font-weight:800;">Teras LA DineHub</p>
          <p style="margin:6px 0 0;color:#d9e4dd;font-size:13px;">Kamu berhak atas pengembalian dana</p>
        </td></tr>

        <tr><td style="padding:24px 24px 8px;">
          <p style="margin:0 0 4px;font-size:15px;color:#111827;">Halo <b>{nama}</b>,</p>
          <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.6;">
            Sebagian/seluruh pesananmu <b style="color:{BRAND};">{order.order_code}</b> dibatalkan,
            sehingga kamu berhak menerima refund. Pilih metode e-wallet tujuan lewat tombol di bawah.
          </p>
        </td></tr>

        <tr><td style="padding:16px 24px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:14px;">
            <tr><td style="padding:18px;text-align:center;">
              <p style="margin:0 0 4px;font-size:12px;color:#15803d;text-transform:uppercase;letter-spacing:.5px;">Nominal Refund</p>
              <p style="margin:0;font-size:26px;font-weight:800;color:{BRAND};">{_rupiah(nominal)}</p>
            </td></tr>
          </table>
        </td></tr>

        <tr><td align="center" style="padding:8px 24px 28px;">
          <a href="{refund_url}" target="_blank"
             style="display:inline-block;background:linear-gradient(135deg,{BRAND_LIGHT} 0%,{BRAND} 100%);
                    color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;
                    padding:14px 28px;border-radius:14px;box-shadow:0 6px 16px rgba(29,58,39,.32);">
            Pilih Metode Refund
          </a>
          <p style="margin:14px 0 0;font-size:11px;color:#9ca3af;line-height:1.5;">
            Tombol tidak berfungsi? Salin tautan ini:<br>
            <span style="color:{GOLD};word-break:break-all;">{refund_url}</span>
          </p>
        </td></tr>

        <tr><td style="background:#f9fafb;padding:18px 24px;border-top:1px solid #eef0f2;">
          <p style="margin:0;font-size:11px;color:#9ca3af;line-height:1.6;">
            Email otomatis dari Teras LA DineHub. Mohon jangan balas email ini.
          </p>
        </td></tr>

      </table>
      <p style="margin:14px 0 0;font-size:11px;color:#b0b6bd;">© Teras LA DineHub</p>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(to: str, subject: str, html: str) -> None:
    """Kirim email HTML via SMTP. Aman dipanggil di background task — error
    di-log, tidak dilempar."""
    if not (settings.admin_email and settings.admin_email_password):
        print("[email] dilewati: ADMIN_EMAIL / ADMIN_EMAIL_PASSWORD belum diset")
        return
    if not to:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.email_from_name} <{settings.admin_email}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            server.login(settings.admin_email, settings.admin_email_password)
            server.sendmail(settings.admin_email, [to], msg.as_string())
        print(f"[email] terkirim ke {to}: {subject}")
    except Exception as exc:  # noqa: BLE001
        print(f"[email] gagal kirim ke {to}: {exc}")
